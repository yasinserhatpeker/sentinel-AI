from django.http import JsonResponse
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView
from .models import InventoryReservation, StockItem
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


class WorkflowReservationView(APIView):
    def post(self, request):
        order_reference = request.data.get("order_reference", "")
        if not isinstance(order_reference, str) or not order_reference:
            return Response({"detail": "invalid_workflow_payload"}, status=status.HTTP_400_BAD_REQUEST)
        reservation, created = InventoryReservation.objects.get_or_create(order_reference=order_reference, defaults={"sku": "workflow-demo", "quantity": 1})
        if created:
            reconcile_stock.delay(reservation.sku)
            publish_queue_event("inventory", "queued", [("queue.enqueue_rate", 1.0, "tasks")])
        return Response({"order_reference": reservation.order_reference, "created": created}, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)
