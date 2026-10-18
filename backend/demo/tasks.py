from celery import shared_task
from django.core.cache import cache

from .models import Order
from .telemetry import record_report_task_dequeued, record_report_task_failed
from .telemetry_ingestion import aggregate_minute, completed_minute_start, purge_expired_events


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


@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, max_retries=3)
def aggregate_completed_telemetry_minute(self, window_start: str | None = None) -> int:
    """Aggregate a completed UTC minute; update-or-create makes retried windows safe."""

    if window_start:
        from datetime import datetime

        requested_window = datetime.fromisoformat(window_start.replace("Z", "+00:00"))
    else:
        requested_window = completed_minute_start()
    return aggregate_minute(requested_window)


@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, max_retries=3)
def purge_expired_telemetry(self) -> int:
    """Enforce the approved 30-day local raw-telemetry retention period."""

    return purge_expired_events()
