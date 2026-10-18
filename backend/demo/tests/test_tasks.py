from django.test import TestCase, override_settings

from demo.models import Order
from demo.tasks import generate_order_report


@override_settings(CACHES={"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}})
class GenerateOrderReportTests(TestCase):
    def test_duplicate_delivery_keeps_report_ready(self) -> None:
        order = Order.objects.create(reference="ORDER-002", amount="10.00", status=Order.Status.REPORT_QUEUED)

        first = generate_order_report.run(str(order.id))
        second = generate_order_report.run(str(order.id))

        order.refresh_from_db()
        self.assertEqual(first["status"], "ready")
        self.assertEqual(second["status"], "already_ready")
        self.assertEqual(order.status, Order.Status.REPORT_READY)

