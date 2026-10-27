from django.http import JsonResponse
from rest_framework import generics

from .models import PaymentAuthorization
from .serializers import PaymentAuthorizationSerializer
from .tasks import settle_authorization
from common.queue import publish_queue_event


def health(_request):
    return JsonResponse({"status": "ok", "service": "payments-api"})


class PaymentAuthorizationListCreateView(generics.ListCreateAPIView):
    queryset = PaymentAuthorization.objects.order_by("-created_at")
    serializer_class = PaymentAuthorizationSerializer

    def perform_create(self, serializer):
        authorization = serializer.save()
        settle_authorization.delay(authorization.reference)
        publish_queue_event("payments", "queued", [("queue.enqueue_rate", 1.0, "tasks")])


class PaymentAuthorizationDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = PaymentAuthorization.objects.all()
    serializer_class = PaymentAuthorizationSerializer
    lookup_field = "reference"
