from datetime import timedelta
from uuid import uuid4

from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from demo.models import TelemetryAggregate, TelemetryEvent
from demo.telemetry_ingestion import aggregate_minute, purge_expired_events
from demo.tests.helpers import bearer_token, create_superuser


class TelemetryIngestionTests(TestCase):
    def setUp(self) -> None:
        self.client = APIClient()
        self.user = create_superuser()
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
            HTTP_AUTHORIZATION=bearer_token(self.user),
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
        self.assertTrue(TelemetryAggregate.objects.exists())

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
        self.assertEqual(unauthorized_response.data, {"error": {"code": "authentication_required"}})
        self.assertEqual(TelemetryEvent.objects.count(), 0)

    @override_settings(SECRET_KEY="test-django-secret")
    def test_local_machine_signature_can_ingest_without_a_browser_jwt(self) -> None:
        from demo.machine_authentication import DemoTelemetryTokenAuthentication

        accepted = self.client.post(
            "/api/telemetry/v1/",
            self.payload(),
            format="json",
            HTTP_X_TELEMETRY_SIGNATURE=DemoTelemetryTokenAuthentication.expected_signature(),
        )
        denied = self.client.post(
            "/api/telemetry/v1/",
            self.payload(),
            format="json",
            HTTP_X_TELEMETRY_SIGNATURE="wrong-signature",
        )

        self.assertEqual(accepted.status_code, 202)
        self.assertEqual(denied.status_code, 401)
        self.assertEqual(denied.data, {"error": {"code": "authentication_failed"}})

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

    def test_scoped_aggregate_contract_does_not_expose_raw_events(self) -> None:
        window = self.observed_at.replace(second=0, microsecond=0)
        self.post(
            self.payload(
                observed_at=(window + timedelta(seconds=1)).isoformat(),
                metric={"name": "http.server.duration", "value": 120.0, "unit": "ms"},
            )
        )
        aggregate_minute(window)

        response = self.client.get(
            "/api/telemetry/v1/aggregates/",
            {
                "environment": "local",
                "service": "sentinel-demo-api",
                "start": window.isoformat(),
                "end": (window + timedelta(minutes=1)).isoformat(),
            },
            HTTP_AUTHORIZATION=bearer_token(self.user),
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["schema_version"], "telemetry.v1")
        self.assertEqual(response.data["scope"]["service"], "sentinel-demo-api")
        self.assertEqual(len(response.data["points"]), 1)
        self.assertNotIn("dimensions", response.data["points"][0])
        self.assertNotIn("event_id", response.data["points"][0])

    def test_aggregate_contract_denies_missing_scope_unknown_service_and_broad_range(self) -> None:
        missing_scope = self.client.get(
            "/api/telemetry/v1/aggregates/", HTTP_AUTHORIZATION=bearer_token(self.user)
        )
        unknown_service = self.client.get(
            "/api/telemetry/v1/aggregates/",
            {
                "environment": "local",
                "service": "unknown-service",
                "start": self.observed_at.isoformat(),
                "end": (self.observed_at + timedelta(minutes=1)).isoformat(),
            },
            HTTP_AUTHORIZATION=bearer_token(self.user),
        )
        broad_range = self.client.get(
            "/api/telemetry/v1/aggregates/",
            {
                "environment": "local",
                "service": "sentinel-demo-api",
                "start": self.observed_at.isoformat(),
                "end": (self.observed_at + timedelta(hours=25)).isoformat(),
            },
            HTTP_AUTHORIZATION=bearer_token(self.user),
        )

        self.assertEqual(missing_scope.status_code, 400)
        self.assertEqual(unknown_service.status_code, 404)
        self.assertEqual(unknown_service.data, {"error": {"code": "telemetry_service_not_found"}})
        self.assertEqual(broad_range.status_code, 400)

    def test_service_discovery_requires_environment_scope(self) -> None:
        denied = self.client.get("/api/telemetry/v1/services/", HTTP_AUTHORIZATION=bearer_token(self.user))
        allowed = self.client.get(
            "/api/telemetry/v1/services/",
            {"environment": "local"},
            HTTP_AUTHORIZATION=bearer_token(self.user),
        )

        self.assertEqual(denied.status_code, 400)
        self.assertEqual(allowed.status_code, 200)
        self.assertEqual(allowed.data, {"environment": "local", "services": []})
