from celery import shared_task
from django.core.cache import cache

from .models import Order
from .telemetry import record_report_task_dequeued, record_report_task_failed


@shared_task(bind=True, autoretry_for=(Order.DoesNotExist,), retry_backoff=True, max_retries=3)
def generate_order_report(self, order_id: str) -> dict[str, str]:
    """Create a deterministic local report marker; safe when delivered more than once."""

    record_report_task_dequeued()
    try:
        cache_key = f"demo-report:{order_id}"
        if cache.get(cache_key):
            return {"order_id": order_id, "status": "already_ready"}

        order = Order.objects.get(pk=order_id)
        cache.set(cache_key, "ready", timeout=3600)
        if order.status != Order.Status.REPORT_READY:
            order.status = Order.Status.REPORT_READY
            order.save(update_fields=("status", "updated_at"))
        return {"order_id": order_id, "status": "ready"}
    except Exception:
        record_report_task_failed()
        raise
