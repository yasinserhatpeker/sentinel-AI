from django.http import JsonResponse
from rest_framework import generics
from .models import Order
from .serializers import OrderSerializer
from .tasks import process_order
from common.queue import publish_queue_event


def health(_request):
    return JsonResponse({"status": "ok", "service": "orders-api"})


class OrderListCreateView(generics.ListCreateAPIView):
    queryset = Order.objects.order_by("-created_at")
    serializer_class = OrderSerializer

    def perform_create(self, serializer):
        order = serializer.save()
        process_order.delay(order.reference)
        publish_queue_event("orders", "queued", [("queue.enqueue_rate", 1.0, "tasks")])


class OrderDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Order.objects.all()
    serializer_class = OrderSerializer
    lookup_field = "reference"
