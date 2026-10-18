import os
from threading import Lock

from opentelemetry import metrics, trace
from opentelemetry.metrics import Observation
from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.celery import CeleryInstrumentor
from opentelemetry.instrumentation.django import DjangoInstrumentor
from opentelemetry.instrumentation.psycopg import PsycopgInstrumentor
from opentelemetry.instrumentation.redis import RedisInstrumentor
from opentelemetry.instrumentation.system_metrics import SystemMetricsInstrumentor
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

_configured = False
_lock = Lock()
_queue_metrics = None


def _queue_depth_callback(_options):
    """Read the local Celery list length without adding message payload to telemetry."""

    try:
        import redis

        client = redis.from_url(os.environ.get("REDIS_URL", "redis://localhost:6379/0"))
        return [Observation(client.llen("celery"), {"messaging.destination.name": "celery"})]
    except Exception:
        return []


def record_report_task_enqueued() -> None:
    if _queue_metrics is not None:
        _queue_metrics["enqueued"].add(1, {"messaging.destination.name": "celery"})


def record_report_task_dequeued() -> None:
    if _queue_metrics is not None:
        _queue_metrics["dequeued"].add(1, {"messaging.destination.name": "celery"})


def record_report_task_failed() -> None:
    if _queue_metrics is not None:
        _queue_metrics["failed"].add(1, {"messaging.destination.name": "celery"})


def configure_telemetry() -> None:
    global _configured, _queue_metrics
    with _lock:
        if _configured:
            return

        endpoint = os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT")
        if not endpoint:
            return

        resource = Resource.create({"service.name": os.environ.get("OTEL_SERVICE_NAME", "sentinel-demo")})
        tracer_provider = TracerProvider(resource=resource)
        tracer_provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter(endpoint=f"{endpoint}/v1/traces")))
        trace.set_tracer_provider(tracer_provider)

        metric_reader = PeriodicExportingMetricReader(
            OTLPMetricExporter(endpoint=f"{endpoint}/v1/metrics"), export_interval_millis=5000
        )
        metrics.set_meter_provider(MeterProvider(resource=resource, metric_readers=[metric_reader]))

        meter = metrics.get_meter("sentinel.demo.queue")
        meter.create_observable_gauge(
            "sentinel.queue.depth",
            callbacks=[_queue_depth_callback],
            unit="{messages}",
            description="Messages waiting in the local Celery queue.",
        )
        _queue_metrics = {
            "enqueued": meter.create_counter("sentinel.queue.enqueue.count", unit="{messages}"),
            "dequeued": meter.create_counter("sentinel.queue.dequeue.count", unit="{messages}"),
            "failed": meter.create_counter("sentinel.queue.failed.count", unit="{tasks}"),
        }

        DjangoInstrumentor().instrument()
        PsycopgInstrumentor().instrument()
        RedisInstrumentor().instrument()
        CeleryInstrumentor().instrument()
        SystemMetricsInstrumentor().instrument()
        _configured = True
