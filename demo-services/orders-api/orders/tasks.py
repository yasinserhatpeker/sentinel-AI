import uuid

from celery import shared_task

from common.internal_client import DependencyRequestError, post_json
from common.queue import publish_queue_event

from .models import Order


@shared_task(bind=True, autoretry_for=(DependencyRequestError,), retry_backoff=True, retry_kwargs={"max_retries": 3})
def process_order(self, reference: str) -> None:
    try:
        order = Order.objects.get(reference=reference)
        correlation_id = str(uuid.uuid5(uuid.NAMESPACE_URL, f"sentinelai-order:{reference}"))
        payload = {"order_reference": reference, "amount": str(order.total)}
        post_json("http://payments-api:8080/v1/workflow/authorize/", payload, correlation_id, "payments-api")
        post_json("http://inventory-api:8080/v1/workflow/reserve/", {"order_reference": reference}, correlation_id, "inventory-api")
        post_json("http://notifications-api:8080/v1/workflow/notify/", {"order_reference": reference}, correlation_id, "notifications-api")
        post_json("http://reporting-worker:8080/v1/workflow/report/", {"order_reference": reference}, correlation_id, "reporting-worker")
        Order.objects.filter(pk=order.pk).update(status="processed")
        publish_queue_event("orders", "completed", [("queue.dequeue_rate", 1.0, "tasks")])
    except DependencyRequestError:
        if self.request.retries >= self.max_retries:
            Order.objects.filter(reference=reference).update(status="failed")
        publish_queue_event("orders", "failed", [("queue.failed_task_count", 1.0, "tasks")])
        raise
    except Exception:
        Order.objects.filter(reference=reference).update(status="failed")
        publish_queue_event("orders", "failed", [("queue.failed_task_count", 1.0, "tasks")])
        raise
