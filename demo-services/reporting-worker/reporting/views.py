from django.http import JsonResponse
from rest_framework import generics

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
