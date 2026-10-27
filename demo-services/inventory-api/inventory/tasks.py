from celery import shared_task
from django.utils import timezone

from common.queue import publish_queue_event

from .models import StockItem


@shared_task
def reconcile_stock(sku: str) -> None:
    try:
        StockItem.objects.filter(sku=sku).update(updated_at=timezone.now())
        publish_queue_event("inventory", "completed", [("queue.dequeue_rate", 1.0, "tasks")])
    except Exception:
        publish_queue_event("inventory", "failed", [("queue.failed_task_count", 1.0, "tasks")])
        raise
