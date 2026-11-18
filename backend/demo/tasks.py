from datetime import timedelta

from celery import shared_task
from django.core.cache import cache

from .models import Order
from .telemetry import record_report_task_dequeued, record_report_task_failed
from .telemetry_ingestion import (
    aggregate_minute,
    backfill_feature_windows,
    completed_minute_start,
    feature_window_start,
    materialize_feature_window,
    purge_expired_events,
)


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


@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, max_retries=3)
def materialize_completed_telemetry_features(self, window_start: str | None = None) -> int:
    """Write and score retry-safe five-minute feature vectors."""

    if window_start:
        from datetime import datetime

        requested_window = datetime.fromisoformat(window_start.replace("Z", "+00:00"))
    else:
        # Beat may run a few minutes into the current five-minute bucket. Use
        # the previous bucket so all five source minutes are complete instead
        # of repeatedly selecting an in-progress window that cannot materialize.
        requested_window = feature_window_start(completed_minute_start()) - timedelta(minutes=5)
    materialized = materialize_feature_window(requested_window)
    from .detection.service import score_feature_window
    from .detection.evaluation import evaluate_experiments_for_window

    completed_window = feature_window_start(requested_window)
    score_feature_window(completed_window)
    evaluate_experiments_for_window(completed_window)
    return materialized


@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, max_retries=3)
def backfill_telemetry_features(self, start: str, end: str) -> int:
    """Bounded internal backfill for local model-training features."""

    from datetime import datetime

    return backfill_feature_windows(
        datetime.fromisoformat(start.replace("Z", "+00:00")),
        datetime.fromisoformat(end.replace("Z", "+00:00")),
    )


@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, max_retries=3)
def recover_expired_fault_experiments(self) -> int:
    """Watchdog that clears expired local faults and closes recovery windows."""

    from .faults import recover_expired_experiments

    return recover_expired_experiments()
