from django.http import JsonResponse
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView

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


class WorkflowAuthorizationView(APIView):
    def post(self, request):
        order_reference = request.data.get("order_reference", "")
        amount = request.data.get("amount")
        if not isinstance(order_reference, str) or not order_reference or amount is None:
            return Response({"detail": "invalid_workflow_payload"}, status=status.HTTP_400_BAD_REQUEST)
        authorization, created = PaymentAuthorization.objects.get_or_create(
            reference=f"wf-{order_reference}"[:48], defaults={"order_reference": order_reference, "amount": amount}
        )
        if created:
            settle_authorization.delay(authorization.reference)
            publish_queue_event("payments", "queued", [("queue.enqueue_rate", 1.0, "tasks")])
        return Response({"reference": authorization.reference, "created": created}, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)
