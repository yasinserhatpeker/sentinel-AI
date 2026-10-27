from celery import shared_task

from common.queue import publish_queue_event

from .models import Notification


@shared_task
def deliver_notification(notification_id: int) -> None:
    try:
        Notification.objects.filter(pk=notification_id).update(status="delivered")
        publish_queue_event("notifications", "completed", [("queue.dequeue_rate", 1.0, "tasks")])
    except Exception:
        publish_queue_event("notifications", "failed", [("queue.failed_task_count", 1.0, "tasks")])
        raise
