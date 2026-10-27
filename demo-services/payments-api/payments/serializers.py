from rest_framework import serializers

from .models import PaymentAuthorization


class PaymentAuthorizationSerializer(serializers.ModelSerializer):
    class Meta:
        model = PaymentAuthorization
        fields = ("reference", "order_reference", "amount", "status", "created_at")
        read_only_fields = ("status", "created_at")
