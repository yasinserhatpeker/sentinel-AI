from unittest.mock import patch

from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from demo.models import Order


@override_settings(DEMO_API_TOKEN="test-token")
class OrderCreateTests(TestCase):
    def setUp(self) -> None:
        self.client = APIClient()

    def test_health_check_is_public(self) -> None:
        response = self.client.get("/api/health/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, {"status": "ok"})

    @patch("demo.views.generate_order_report.delay")
    def test_valid_token_creates_order_caches_reference_and_queues_report(self, delay) -> None:
        delay.return_value.id = "task-123"
        response = self.client.post(
            "/api/orders/",
            {"reference": "ORDER-001", "amount": "19.99"},
            format="json",
            HTTP_AUTHORIZATION="Demo test-token",
        )

        self.assertEqual(response.status_code, 201)
        order = Order.objects.get(reference="ORDER-001")
        self.assertEqual(order.status, Order.Status.REPORT_QUEUED)
        delay.assert_called_once_with(str(order.id))

    def test_missing_token_is_denied_with_stable_error_shape(self) -> None:
        response = self.client.post("/api/orders/", {"reference": "ORDER-001", "amount": "19.99"}, format="json")

        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.data, {"error": {"code": "demo_token_required"}})
