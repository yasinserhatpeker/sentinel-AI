from django.http import JsonResponse
from rest_framework import generics
from .models import Notification
from .serializers import NotificationSerializer
from .tasks import deliver_notification
from common.queue import publish_queue_event


def health(_request):
    return JsonResponse({"status": "ok", "service": "notifications-api"})


class NotificationListCreateView(generics.ListCreateAPIView):
    queryset = Notification.objects.order_by("-created_at")
    serializer_class = NotificationSerializer

    def perform_create(self, serializer):
        notification = serializer.save()
        deliver_notification.delay(notification.pk)
        publish_queue_event("notifications", "queued", [("queue.enqueue_rate", 1.0, "tasks")])


class NotificationDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Notification.objects.all()
    serializer_class = NotificationSerializer
