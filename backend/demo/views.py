from django.core.cache import cache
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Order
from .serializers import OrderCreateSerializer, OrderSerializer, TelemetryBatchSerializer
from .tasks import generate_order_report
from .telemetry import record_report_task_enqueued
from .telemetry_ingestion import persist_metric_events


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
    def post(self, request):
        serializer = TelemetryBatchSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        inserted, duplicates = persist_metric_events(serializer.validated_data["events"])
        return Response(
            {
                "schema_version": serializer.validated_data["schema_version"],
                "accepted": inserted,
                "duplicates": duplicates,
            },
            status=status.HTTP_202_ACCEPTED,
        )
