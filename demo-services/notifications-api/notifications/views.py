from django.http import JsonResponse
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView
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


class WorkflowNotificationView(APIView):
    def post(self, request):
        order_reference = request.data.get("order_reference", "")
        if not isinstance(order_reference, str) or not order_reference:
            return Response({"detail": "invalid_workflow_payload"}, status=status.HTTP_400_BAD_REQUEST)
        notification, created = Notification.objects.get_or_create(workflow_key=f"order:{order_reference}"[:96], defaults={"recipient_reference": order_reference, "channel": "email"})
        if created:
            deliver_notification.delay(notification.pk)
            publish_queue_event("notifications", "queued", [("queue.enqueue_rate", 1.0, "tasks")])
        return Response({"id": notification.pk, "created": created}, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)
