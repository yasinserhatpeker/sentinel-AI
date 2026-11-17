from datetime import timedelta
from unittest.mock import patch

from django.test import TestCase
from django.utils import timezone

from .models import ReportJob
from .tasks import oldest_queued_age_seconds


class QueueAgeTests(TestCase):
    def test_zero_broker_depth_ignores_orphaned_queued_row(self) -> None:
        job = ReportJob.objects.create(report_type="readiness-workload")
        ReportJob.objects.filter(pk=job.pk).update(created_at=timezone.now() - timedelta(hours=2))

        self.assertEqual(oldest_queued_age_seconds(depth=0), 0.0)

    def test_positive_broker_depth_reports_database_queue_age(self) -> None:
        job = ReportJob.objects.create(report_type="readiness-workload")
        ReportJob.objects.filter(pk=job.pk).update(created_at=timezone.now() - timedelta(seconds=30))

        self.assertGreaterEqual(oldest_queued_age_seconds(depth=1), 29.0)

    @patch("reporting.tasks.queue_depth", return_value=0)
    def test_default_depth_is_read_from_broker(self, mocked_depth) -> None:
        ReportJob.objects.create(report_type="readiness-workload")

        self.assertEqual(oldest_queued_age_seconds(), 0.0)
        mocked_depth.assert_called_once_with()
