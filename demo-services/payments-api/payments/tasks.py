from celery import shared_task

from common.queue import publish_queue_event

from .models import PaymentAuthorization


@shared_task
def settle_authorization(reference: str) -> None:
    try:
        PaymentAuthorization.objects.filter(reference=reference).update(status="settled")
        publish_queue_event("payments", "completed", [("queue.dequeue_rate", 1.0, "tasks")])
    except Exception:
        publish_queue_event("payments", "failed", [("queue.failed_task_count", 1.0, "tasks")])
        raise
