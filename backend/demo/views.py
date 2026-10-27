from django.core.cache import cache
from django.db.models import QuerySet
from rest_framework import permissions, status
from rest_framework.exceptions import NotFound
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.authentication import JWTAuthentication

from .machine_authentication import DemoTelemetryTokenAuthentication
from .models import Order, TelemetryAggregate
from .serializers import (
    OrderCreateSerializer,
    OrderSerializer,
    TelemetryAggregateQuerySerializer,
    TelemetryBatchSerializer,
    TelemetryServiceQuerySerializer,
)
from .tasks import generate_order_report
from .telemetry import record_report_task_enqueued
from .telemetry_ingestion import aggregate_minute, persist_metric_events


class HealthView(APIView):
    authentication_classes = []
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        return Response({"status": "ok"})


class OrderCreateView(APIView):
    def post(self, request):
        serializer = OrderCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        order = serializer.save(status=Order.Status.REPORT_QUEUED)
        cache.set(f"demo-order:{order.id}", order.reference, timeout=300)
        task = generate_order_report.delay(str(order.id))
        record_report_task_enqueued()
        return Response(
            {"order": OrderSerializer(order).data, "report_task_id": task.id},
            status=status.HTTP_201_CREATED,
        )


class TelemetryIngestView(APIView):
    # Browser users retain JWT access; local demo containers use a secret-derived signature.
    authentication_classes = [DemoTelemetryTokenAuthentication, JWTAuthentication]

    def post(self, request):
        serializer = TelemetryBatchSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        events = serializer.validated_data["events"]
        inserted, duplicates = persist_metric_events(events)
        # Keep the local dashboard responsive after a genuine service request.
        # The periodic task still recomputes completed windows; this upsert only
        # exposes the in-progress minute sooner and never fabricates a value.
        for window in {event["observed_at"].replace(second=0, microsecond=0) for event in events}:
            aggregate_minute(window)
        return Response(
            {
                "schema_version": serializer.validated_data["schema_version"],
                "accepted": inserted,
                "duplicates": duplicates,
            },
            status=status.HTTP_202_ACCEPTED,
        )


class TelemetryServiceListView(APIView):
    """Expose locally available aggregate services for an explicit environment."""

    def get(self, request):
        serializer = TelemetryServiceQuerySerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        services = (
            TelemetryAggregate.objects.filter(environment=serializer.validated_data["environment"])
            .order_by("service")
            .values_list("service", flat=True)
            .distinct()
        )
        return Response({"environment": serializer.validated_data["environment"], "services": list(services)})


class TelemetryAggregateListView(APIView):
    """Return bounded aggregate telemetry without disclosing raw events or dimensions."""

    def get(self, request):
        serializer = TelemetryAggregateQuerySerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        scope = serializer.validated_data
        aggregates: QuerySet[TelemetryAggregate] = TelemetryAggregate.objects.filter(
            environment=scope["environment"],
            service=scope["service"],
            window_start__gte=scope["start"],
            window_start__lt=scope["end"],
        ).order_by("window_start", "metric_name", "instance")

        if not TelemetryAggregate.objects.filter(
            environment=scope["environment"], service=scope["service"]
        ).exists():
            raise NotFound("telemetry_service_not_found")

        points = [
            {
                "timestamp": aggregate.window_start,
                "metric": aggregate.metric_name,
                "unit": aggregate.unit,
                "count": aggregate.event_count,
                "minimum": aggregate.minimum,
                "maximum": aggregate.maximum,
                "average": aggregate.average,
                "last": aggregate.last_value,
                "p50": aggregate.p50,
                "p95": aggregate.p95,
                "p99": aggregate.p99,
            }
            for aggregate in aggregates
        ]
        metrics = {point["metric"] for point in points}
        groups = {
            "http": {"http.server.request_count", "http.server.error_rate", "http.server.duration"},
            "runtime": {"runtime.cpu.usage", "runtime.memory.usage"},
            "database": {"db.connection.usage", "db.query.duration"},
            "queue": {
                "queue.depth",
                "queue.oldest_message_age",
                "queue.enqueue_rate",
                "queue.dequeue_rate",
                "queue.failed_task_count",
            },
        }
        availability = {name: bool(required & metrics) for name, required in groups.items()}
        return Response(
            {
                "schema_version": "telemetry.v1",
                "scope": {
                    "environment": scope["environment"],
                    "service": scope["service"],
                    "start": scope["start"],
                    "end": scope["end"],
                },
                "availability": availability,
                "points": points,
            }
        )
