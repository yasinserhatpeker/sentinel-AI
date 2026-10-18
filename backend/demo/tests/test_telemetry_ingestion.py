from datetime import timedelta
from uuid import uuid4

from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from demo.models import TelemetryAggregate, TelemetryEvent
from demo.telemetry_ingestion import aggregate_minute, purge_expired_events


@override_settings(DEMO_API_TOKEN="test-token")
class TelemetryIngestionTests(TestCase):
    def setUp(self) -> None:
        self.client = APIClient()
        self.observed_at = timezone.now().replace(second=10, microsecond=0)

    def payload(self, **event_overrides):
        event = {
            "event_id": str(uuid4()),
            "observed_at": self.observed_at.isoformat(),
            "metric": {"name": "http.server.duration", "value": 120.0, "unit": "ms"},
            "context": {
                "environment": "local",
                "service": "sentinel-demo-api",
                "instance": "api-1",
                "deployment_id": "demo-1",
                "trace_id": "0123456789abcdef",
            },
            "dimensions": {"route": "orders.create", "status_class": "2xx"},
        }
        event.update(event_overrides)
        return {"schema_version": "telemetry.v1", "events": [event]}

    def post(self, payload):
        return self.client.post(
            "/api/telemetry/v1/",
            payload,
            format="json",
            HTTP_AUTHORIZATION="Demo test-token",
        )

    def test_valid_batch_is_normalized_and_stored(self) -> None:
        response = self.post(self.payload())

        self.assertEqual(response.status_code, 202)
        self.assertEqual(response.data, {"schema_version": "telemetry.v1", "accepted": 1, "duplicates": 0})
        event = TelemetryEvent.objects.get()
        self.assertEqual(event.environment, "local")
        self.assertEqual(event.metric_name, "http.server.duration")
        self.assertTrue(event.dimensions_fingerprint)
        self.assertIsNotNone(event.ingested_at)

    def test_duplicate_delivery_is_safe(self) -> None:
        payload = self.payload()

        first = self.post(payload)
        second = self.post(payload)

        self.assertEqual(first.data["accepted"], 1)
        self.assertEqual(second.data, {"schema_version": "telemetry.v1", "accepted": 0, "duplicates": 1})
        self.assertEqual(TelemetryEvent.objects.count(), 1)

    def test_invalid_or_unauthorized_payload_is_rejected_without_partial_write(self) -> None:
        malformed = {"schema_version": "telemetry.v1", "events": []}
        malformed_response = self.post(malformed)
        unauthorized_response = self.client.post("/api/telemetry/v1/", self.payload(), format="json")

        self.assertEqual(malformed_response.status_code, 400)
        self.assertEqual(malformed_response.data, {"error": {"code": "validation_failed"}})
        self.assertEqual(unauthorized_response.status_code, 401)
        self.assertEqual(unauthorized_response.data, {"error": {"code": "demo_token_required"}})
        self.assertEqual(TelemetryEvent.objects.count(), 0)

    def test_aggregation_is_deterministic_and_safe_to_retry(self) -> None:
        window = self.observed_at.replace(second=0, microsecond=0)
        values = [10.0, 20.0, 30.0, 40.0]
        for index, value in enumerate(values):
            response = self.post(
                self.payload(
                    observed_at=(window + timedelta(seconds=index + 1)).isoformat(),
                    metric={"name": "runtime.cpu.usage", "value": value, "unit": "percent"},
                )
            )
            self.assertEqual(response.status_code, 202)

        first = aggregate_minute(window)
        second = aggregate_minute(window)

        self.assertEqual(first, 1)
        self.assertEqual(second, 1)
        self.assertEqual(TelemetryAggregate.objects.count(), 1)
        aggregate = TelemetryAggregate.objects.get()
        self.assertEqual(aggregate.event_count, 4)
        self.assertEqual(aggregate.minimum, 10.0)
        self.assertEqual(aggregate.maximum, 40.0)
        self.assertEqual(aggregate.average, 25.0)
        self.assertEqual(aggregate.last_value, 40.0)
        self.assertEqual(aggregate.p50, 25.0)
        self.assertAlmostEqual(aggregate.p95, 38.5)
        self.assertAlmostEqual(aggregate.p99, 39.7)

    def test_retention_removes_only_expired_raw_events(self) -> None:
        self.post(self.payload())
        event = TelemetryEvent.objects.get()
        TelemetryEvent.objects.filter(pk=event.pk).update(ingested_at=timezone.now() - timedelta(days=31))

        deleted = purge_expired_events()

        self.assertEqual(deleted, 1)
        self.assertFalse(TelemetryEvent.objects.exists())
