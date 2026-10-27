from unittest.mock import patch

from django.test import TestCase
from rest_framework.test import APIClient

from demo.models import Order
from demo.tests.helpers import bearer_token, create_superuser


class OrderCreateTests(TestCase):
    def setUp(self) -> None:
        self.client = APIClient()
        self.user = create_superuser()

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
            HTTP_AUTHORIZATION=bearer_token(self.user),
        )

        self.assertEqual(response.status_code, 201)
        order = Order.objects.get(reference="ORDER-001")
        self.assertEqual(order.status, Order.Status.REPORT_QUEUED)
        delay.assert_called_once_with(str(order.id))

    def test_missing_token_is_denied_with_stable_error_shape(self) -> None:
        response = self.client.post("/api/orders/", {"reference": "ORDER-001", "amount": "19.99"}, format="json")

        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.data, {"error": {"code": "authentication_required"}})
