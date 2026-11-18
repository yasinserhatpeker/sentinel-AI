from datetime import timedelta

from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from demo.models import FaultExperiment, TelemetryAggregate
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
        self.aggregate("orders-api", "http.server.request_count", 1.0)
        self.aggregate("orders-api", "http.server.error_rate", 0.0)
        self.aggregate("orders-api", "runtime.cpu.usage", 35.0)
        self.aggregate("orders-api", "runtime.memory.usage", 128.0)
        self.aggregate("orders-api", "db.connection.usage", 3.0)
        self.aggregate("orders-api", "db.query.duration", 18.0)
        self.aggregate("orders-api", "queue.depth", 2.0)
        self.aggregate("orders-api", "queue.oldest_message_age", 6.0)
        self.aggregate("payments-api", "http.server.duration", 240.0)
        self.aggregate("payments-api", "http.server.error_rate", 4.0)
        self.aggregate("payments-api", "queue.depth", 7.0)

        response = self.get()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["schema_version"], "overview.v2")
        self.assertEqual(response.data["environment"], "local")
        self.assertEqual(response.data["healthy_service_count"], 1)
        self.assertEqual(response.data["degraded_service_count"], 1)
        self.assertEqual(response.data["slowest_service"], {"service": "payments-api", "p95_latency_ms": 240.0})
        self.assertEqual(response.data["busiest_queue"], {"service": "payments-api", "queue_depth": 7.0})
        orders = next(item for item in response.data["services"] if item["service"] == "orders-api")
        self.assertEqual(orders["request_count"], 1)
        self.assertEqual(orders["error_rate_percent"], 0.0)
        self.assertEqual(orders["cpu_percent"], 35.0)
        self.assertEqual(orders["memory_mb"], 128.0)
        self.assertEqual(orders["db_connections"], 3.0)
        self.assertEqual(orders["db_query_p95_ms"], 18.0)
        self.assertEqual(orders["queue_depth"], 2.0)
        self.assertEqual(orders["queue_oldest_age_seconds"], 6.0)
        self.assertIsNone(orders["anomaly"])
        self.assertIsNone(orders["fault"])
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

    def test_completed_fault_is_history_and_never_reported_as_active(self) -> None:
        completed = FaultExperiment.objects.create(
            environment="local",
            service="orders-api",
            fault_type=FaultExperiment.FaultType.HIGH_LATENCY,
            status=FaultExperiment.Status.COMPLETED,
            parameters={"delay_ms": 500.0},
            duration_seconds=60,
            seed=42,
            created_by=self.user,
        )

        response = self.get()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["active_fault_count"], 0)
        self.assertEqual(response.data["recovering_fault_count"], 0)
        self.assertEqual(response.data["active_faults"], [])
        self.assertEqual(response.data["recovering_faults"], [])
        self.assertIsNone(response.data["latest_fault"])
        self.assertEqual(response.data["latest_completed_fault"]["id"], str(completed.pk))
