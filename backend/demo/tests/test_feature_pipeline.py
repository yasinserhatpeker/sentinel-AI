from datetime import datetime, timedelta
from uuid import uuid4

from django.test import TestCase
from django.utils import timezone

from demo.models import TelemetryAggregate, TelemetryEvent, TelemetryFeature
from demo.telemetry_ingestion import (
    FEATURE_SCHEMA_V1,
    FEATURE_SCHEMA_V2,
    FEATURE_V2_NAMES,
    backfill_feature_windows,
    feature_data_quality_report,
    feature_window_start,
    materialize_feature_window,
    purge_expired_events,
)


class TelemetryFeaturePipelineTests(TestCase):
    def setUp(self) -> None:
        self.window = feature_window_start(timezone.now().replace(second=0, microsecond=0))

    def aggregate(
        self,
        service: str,
        minute: int,
        metric: str,
        value: float,
        *,
        count: int = 1,
        window: datetime | None = None,
    ) -> None:
        timestamp = (window or self.window) + timedelta(minutes=minute)
        TelemetryAggregate.objects.create(
            window_start=timestamp,
            environment="local",
            service=service,
            instance=f"{service}-1",
            deployment_id="compose-local",
            metric_name=metric,
            unit="ms",
            dimensions_fingerprint=f"{service}-{minute}-{metric}",
            event_count=count,
            minimum=value,
            maximum=value,
            average=value,
            last_value=value,
            p50=value,
            p95=value,
            p99=value,
        )

    def test_feature_window_is_deterministic_and_scoped_to_environment_service(self) -> None:
        self.aggregate("orders-api", 0, "http.server.request_count", 1.0, count=4)
        self.aggregate("orders-api", 0, "http.server.error_rate", 0.25, count=4)
        self.aggregate("orders-api", 1, "http.server.duration", 120.0)
        self.aggregate("orders-api", 2, "http.server.duration", 210.0)
        self.aggregate("orders-api", 3, "runtime.cpu.usage", 30.0, count=2)
        self.aggregate("orders-api", 4, "runtime.cpu.usage", 50.0, count=2)
        self.aggregate("orders-api", 4, "queue.depth", 6.0)
        self.aggregate("payments-api", 0, "http.server.duration", 999.0)

        created = materialize_feature_window(self.window)
        feature = TelemetryFeature.objects.get(
            schema_version=FEATURE_SCHEMA_V1,
            environment="local",
            service="orders-api",
            window_start=self.window,
        )

        self.assertEqual(created, 2)
        self.assertEqual(feature.schema_version, FEATURE_SCHEMA_V1)
        self.assertEqual(feature.source_window_count, 5)
        self.assertEqual(feature.request_count, 4.0)
        self.assertEqual(feature.error_rate, 0.25)
        self.assertEqual(feature.latency_p95_ms, 210.0)
        self.assertEqual(feature.cpu_average, 40.0)
        self.assertEqual(feature.queue_depth_max, 6.0)

    def test_backfill_is_idempotent_for_existing_feature_windows(self) -> None:
        self.aggregate("orders-api", 0, "http.server.duration", 125.0)
        start = self.window.isoformat()
        end = (self.window + timedelta(minutes=4)).isoformat()

        first = backfill_feature_windows(datetime.fromisoformat(start), datetime.fromisoformat(end))
        second = backfill_feature_windows(datetime.fromisoformat(start), datetime.fromisoformat(end))

        self.assertEqual(first, 1)
        self.assertEqual(second, 1)
        self.assertEqual(TelemetryFeature.objects.count(), 2)

    def test_raw_retention_does_not_remove_aggregate_or_feature_rows(self) -> None:
        self.aggregate("orders-api", 0, "http.server.duration", 125.0)
        materialize_feature_window(self.window)
        event = TelemetryEvent.objects.create(
            event_id=uuid4(), schema_version="telemetry.v1", observed_at=self.window,
            environment="local", service="orders-api", instance="orders-api-1", deployment_id="compose-local",
            trace_id="trace", metric_name="http.server.duration", metric_value=125.0, unit="ms",
            dimensions={}, dimensions_fingerprint="expired-event",
        )
        TelemetryEvent.objects.filter(pk=event.pk).update(ingested_at=timezone.now() - timedelta(days=31))

        deleted = purge_expired_events()

        self.assertEqual(deleted, 1)
        self.assertFalse(TelemetryEvent.objects.exists())
        self.assertEqual(TelemetryAggregate.objects.count(), 1)
        self.assertEqual(TelemetryFeature.objects.count(), 2)

    def test_feature_v2_adds_time_lag_rolling_and_dependency_context(self) -> None:
        for offset, latency in ((-15, 100.0), (-10, 120.0), (-5, 140.0)):
            historical_window = self.window + timedelta(minutes=offset)
            self.aggregate("orders-api", 0, "http.server.duration", latency, window=historical_window)
            self.aggregate("orders-api", 0, "http.server.error_rate", 0.01, window=historical_window)
            materialize_feature_window(historical_window)

        self.aggregate("orders-api", 0, "http.server.duration", 160.0)
        self.aggregate("orders-api", 0, "http.server.error_rate", 0.02)
        self.aggregate("payments-api", 0, "http.server.duration", 220.0)
        self.aggregate("payments-api", 0, "http.server.error_rate", 0.05)

        materialize_feature_window(self.window)
        orders = TelemetryFeature.objects.get(
            schema_version=FEATURE_SCHEMA_V2,
            environment="local",
            service="orders-api",
            window_start=self.window,
        )
        payments = TelemetryFeature.objects.get(
            schema_version=FEATURE_SCHEMA_V2,
            environment="local",
            service="payments-api",
            window_start=self.window,
        )

        self.assertEqual(set(orders.feature_values), set(FEATURE_V2_NAMES))
        self.assertEqual(len(orders.feature_values), len(FEATURE_V2_NAMES))
        self.assertEqual(orders.feature_values["lag_5m.latency_p95_ms"], 140.0)
        self.assertEqual(orders.feature_values["rolling_15m.latency_p95_ms.mean"], 120.0)
        self.assertEqual(orders.feature_values["rolling_15m.latency_p95_ms.min"], 100.0)
        self.assertEqual(orders.feature_values["rolling_15m.latency_p95_ms.max"], 140.0)
        self.assertIsNotNone(orders.feature_values["time.hour_sin"])
        self.assertEqual(payments.feature_values["dependency.upstream.service_count"], 1.0)
        self.assertEqual(payments.feature_values["dependency.upstream.latency_p95_ms.mean"], 160.0)
        self.assertEqual(payments.feature_values["dependency.upstream.latency_delta_ms"], 60.0)

    def test_feature_v2_does_not_read_future_windows(self) -> None:
        previous = self.window - timedelta(minutes=5)
        future = self.window + timedelta(minutes=5)
        self.aggregate("orders-api", 0, "http.server.duration", 100.0, window=previous)
        materialize_feature_window(previous)
        self.aggregate("orders-api", 0, "http.server.duration", 9999.0, window=future)
        self.aggregate("orders-api", 0, "http.server.duration", 150.0)

        materialize_feature_window(self.window)
        feature = TelemetryFeature.objects.get(
            schema_version=FEATURE_SCHEMA_V2,
            environment="local",
            service="orders-api",
            window_start=self.window,
        )

        self.assertEqual(feature.latency_p95_ms, 150.0)
        self.assertEqual(feature.feature_values["lag_5m.latency_p95_ms"], 100.0)
        self.assertEqual(feature.feature_values["rolling_15m.latency_p95_ms.max"], 100.0)

    def test_feature_quality_report_is_bounded_and_reports_gaps_and_missingness(self) -> None:
        self.aggregate("orders-api", 0, "http.server.duration", 100.0)
        materialize_feature_window(self.window)
        later = self.window + timedelta(minutes=10)
        self.aggregate("orders-api", 0, "http.server.duration", 120.0, window=later)
        materialize_feature_window(later)

        report = feature_data_quality_report(
            environment="local",
            service="orders-api",
            start=self.window,
            end=self.window + timedelta(minutes=15),
        )

        self.assertEqual(report["schema_version"], FEATURE_SCHEMA_V2)
        self.assertEqual(report["sample_count"], 2)
        self.assertEqual(report["expected_window_count"], 3)
        self.assertEqual(report["duplicate_window_count"], 0)
        self.assertEqual(report["sequence_gap_count"], 1)
        self.assertEqual(report["sequence_gaps"], [(self.window + timedelta(minutes=5)).isoformat()])
        self.assertEqual(report["missing_value_count"]["lag_5m.request_count"], 2)

    def test_feature_quality_report_rejects_unbounded_range(self) -> None:
        with self.assertRaisesMessage(ValueError, "feature_quality_range_too_large"):
            feature_data_quality_report(
                environment="local",
                service="orders-api",
                start=self.window,
                end=self.window + timedelta(days=91),
            )
