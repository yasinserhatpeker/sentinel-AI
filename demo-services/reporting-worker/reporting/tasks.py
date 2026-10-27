import os
import uuid

import redis
from celery import shared_task
from django.conf import settings
from django.utils import timezone

from .models import ReportJob
from common.fault import active_fault
from common.telemetry import publish_measurements


def queue_depth() -> int | None:
    """Read the broker's current queue length instead of inventing a value."""
    try:
        client = redis.Redis.from_url(settings.CELERY_BROKER_URL, socket_connect_timeout=1)
        return int(client.llen(settings.CELERY_TASK_DEFAULT_QUEUE))
    except redis.RedisError:
        return None


def oldest_queued_age_seconds() -> float:
    oldest = ReportJob.objects.filter(status="queued").order_by("created_at").first()
    if oldest is None:
        return 0.0
    return max(0.0, (timezone.now() - oldest.created_at).total_seconds())


def publish_queue_measurements(measurements: list[tuple[str, float, str]], outcome: str) -> None:
    service = os.environ.get("SENTINEL_SERVICE_NAME", "reporting-worker")
    publish_measurements(service, uuid.uuid4().hex, measurements, {"queue": settings.CELERY_TASK_DEFAULT_QUEUE, "outcome": outcome})


@shared_task
def complete_report(report_id: int) -> None:
    try:
        # A queue-backlog fault slows real task consumption. Queue depth and
        # age are still read from Redis/database rather than made up.
        fault = active_fault()
        if fault and fault["scenario"] == "queue-backlog":
            import time

            time.sleep(1.5)
        ReportJob.objects.filter(pk=report_id).update(status="completed", completed_at=timezone.now())
        measurements = [("queue.dequeue_rate", 1.0, "tasks"), ("queue.oldest_message_age", oldest_queued_age_seconds(), "seconds")]
        depth = queue_depth()
        if depth is not None:
            measurements.append(("queue.depth", float(depth), "messages"))
        publish_queue_measurements(measurements, "completed")
    except Exception:
        # The failed-task count is published only for a task that actually
        # failed; successful tasks never create a fictitious zero-value event.
        publish_queue_measurements([("queue.failed_task_count", 1.0, "tasks")], "failed")
        raise
