from django.http import JsonResponse
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import ReportJob
from .serializers import ReportJobSerializer
from .tasks import complete_report, oldest_queued_age_seconds, publish_queue_measurements, queue_depth


def health(_request):
    return JsonResponse({"status": "ok", "service": "reporting-worker"})


class ReportJobListCreateView(generics.ListCreateAPIView):
    queryset = ReportJob.objects.order_by("-created_at")
    serializer_class = ReportJobSerializer

    def perform_create(self, serializer):
        report = serializer.save()
        complete_report.delay(report.pk)
        measurements = [("queue.enqueue_rate", 1.0, "tasks"), ("queue.oldest_message_age", oldest_queued_age_seconds(), "seconds")]
        depth = queue_depth()
        if depth is not None:
            measurements.append(("queue.depth", float(depth), "messages"))
        publish_queue_measurements(measurements, "queued")


class ReportJobDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = ReportJob.objects.all()
    serializer_class = ReportJobSerializer


class WorkflowReportView(APIView):
    def post(self, request):
        order_reference = request.data.get("order_reference", "")
        if not isinstance(order_reference, str) or not order_reference:
            return Response({"detail": "invalid_workflow_payload"}, status=status.HTTP_400_BAD_REQUEST)
        report, created = ReportJob.objects.get_or_create(
            workflow_key=f"order:{order_reference}"[:96], defaults={"report_type": "order-workflow"}
        )
        if created:
            complete_report.delay(report.pk)
            measurements = [("queue.enqueue_rate", 1.0, "tasks"), ("queue.oldest_message_age", oldest_queued_age_seconds(), "seconds")]
            depth = queue_depth()
            if depth is not None:
                measurements.append(("queue.depth", float(depth), "messages"))
            publish_queue_measurements(measurements, "queued")
        return Response({"id": report.pk, "created": created}, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)
