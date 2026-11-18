from datetime import datetime, timezone
from unittest.mock import patch

from django.test import TestCase, override_settings

from demo.models import Order
from demo.tasks import generate_order_report, materialize_completed_telemetry_features


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


class CompletedFeatureTaskTests(TestCase):
    @patch("demo.detection.evaluation.evaluate_experiments_for_window")
    @patch("demo.detection.service.score_feature_window")
    @patch("demo.tasks.materialize_feature_window", return_value=5)
    @patch("demo.tasks.completed_minute_start")
    def test_default_run_materializes_the_last_fully_completed_five_minute_window(
        self, completed_minute, materialize, score, evaluate
    ) -> None:
        completed_minute.return_value = datetime(2026, 11, 18, 13, 7, tzinfo=timezone.utc)

        result = materialize_completed_telemetry_features.run()

        expected_window = datetime(2026, 11, 18, 13, 0, tzinfo=timezone.utc)
        self.assertEqual(result, 5)
        materialize.assert_called_once_with(expected_window)
        score.assert_called_once_with(expected_window)
        evaluate.assert_called_once_with(expected_window)

