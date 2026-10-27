from celery import shared_task

from common.queue import publish_queue_event

from .models import Order


@shared_task
def process_order(reference: str) -> None:
    try:
        Order.objects.filter(reference=reference).update(status="processed")
        publish_queue_event("orders", "completed", [("queue.dequeue_rate", 1.0, "tasks")])
    except Exception:
        publish_queue_event("orders", "failed", [("queue.failed_task_count", 1.0, "tasks")])
        raise
