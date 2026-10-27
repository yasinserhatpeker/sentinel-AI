from datetime import datetime, timedelta
from uuid import uuid4

from django.test import TestCase
from django.utils import timezone

from demo.models import TelemetryAggregate, TelemetryEvent, TelemetryFeature
from demo.telemetry_ingestion import (
    backfill_feature_windows,
    feature_window_start,
    materialize_feature_window,
    purge_expired_events,
)


class TelemetryFeaturePipelineTests(TestCase):
    def setUp(self) -> None:
        self.window = feature_window_start(timezone.now().replace(second=0, microsecond=0))

    def aggregate(self, service: str, minute: int, metric: str, value: float, *, count: int = 1) -> None:
        timestamp = self.window + timedelta(minutes=minute)
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
        feature = TelemetryFeature.objects.get(environment="local", service="orders-api", window_start=self.window)

        self.assertEqual(created, 2)
        self.assertEqual(feature.schema_version, "features.v1")
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
        self.assertEqual(TelemetryFeature.objects.count(), 1)

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
        self.assertEqual(TelemetryFeature.objects.count(), 1)
