from datetime import timedelta

from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from demo.models import TelemetryAggregate
from demo.tests.helpers import bearer_token, create_superuser


class SystemOverviewTests(TestCase):
    def setUp(self) -> None:
        self.client = APIClient()
        self.user = create_superuser()
        self.window = timezone.now().replace(second=0, microsecond=0)

    def aggregate(self, service: str, metric_name: str, value: float, *, minutes_ago: int = 0) -> None:
        TelemetryAggregate.objects.create(
            window_start=self.window - timedelta(minutes=minutes_ago),
            environment="local",
            service=service,
            instance=f"{service}-1",
            deployment_id="demo",
            metric_name=metric_name,
            unit="ms" if metric_name == "http.server.duration" else "count",
            dimensions_fingerprint=f"{service}-{metric_name}-{minutes_ago}",
            event_count=1,
            minimum=value,
            maximum=value,
            average=value,
            last_value=value,
            p50=value,
            p95=value,
            p99=value,
        )

    def get(self, params=None):
        return self.client.get(
            "/api/telemetry/v1/overview/",
            {"environment": "local"} if params is None else params,
            HTTP_AUTHORIZATION=bearer_token(self.user),
        )

    def test_overview_is_aggregate_only_and_uses_the_latest_metric_for_each_service(self) -> None:
        self.aggregate("orders-api", "http.server.duration", 90.0, minutes_ago=2)
        self.aggregate("orders-api", "http.server.duration", 180.0)
        self.aggregate("orders-api", "http.server.error_rate", 0.0)
        self.aggregate("payments-api", "http.server.duration", 240.0)
        self.aggregate("payments-api", "http.server.error_rate", 4.0)
        self.aggregate("payments-api", "queue.depth", 7.0)

        response = self.get()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["schema_version"], "overview.v1")
        self.assertEqual(response.data["environment"], "local")
        self.assertEqual(response.data["healthy_service_count"], 1)
        self.assertEqual(response.data["degraded_service_count"], 1)
        self.assertEqual(response.data["slowest_service"], {"service": "payments-api", "p95_latency_ms": 240.0})
        self.assertEqual(response.data["busiest_queue"], {"service": "payments-api", "queue_depth": 7.0})
        self.assertFalse(response.data["fault_context_available"])
        self.assertNotIn("dimensions", response.data)
        self.assertNotIn("trace_id", response.data)
        self.assertEqual(response.data["dependencies"][0], ["orders-api", "payments-api"])

    def test_overview_requires_authentication_and_explicit_environment(self) -> None:
        unauthenticated = self.client.get("/api/telemetry/v1/overview/?environment=local")
        missing_environment = self.get({})

        self.assertEqual(unauthenticated.status_code, 401)
        self.assertEqual(missing_environment.status_code, 400)

    def test_overview_returns_an_empty_bounded_summary_when_no_aggregates_exist(self) -> None:
        response = self.get()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["services"], [])
        self.assertEqual(response.data["healthy_service_count"], 0)
        self.assertEqual(response.data["slowest_service"], None)
        self.assertEqual(response.data["busiest_queue"], None)
