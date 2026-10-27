from django.http import JsonResponse
from rest_framework import generics
from .models import StockItem
from .serializers import StockItemSerializer
from .tasks import reconcile_stock
from common.queue import publish_queue_event


def health(_request):
    return JsonResponse({"status": "ok", "service": "inventory-api"})


class StockListCreateView(generics.ListCreateAPIView):
    queryset = StockItem.objects.order_by("sku")
    serializer_class = StockItemSerializer

    def perform_create(self, serializer):
        item = serializer.save()
        reconcile_stock.delay(item.sku)
        publish_queue_event("inventory", "queued", [("queue.enqueue_rate", 1.0, "tasks")])


class StockDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = StockItem.objects.all()
    serializer_class = StockItemSerializer
    lookup_field = "sku"
