from rest_framework import serializers
from .models import StockItem


class StockItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = StockItem
        fields = ("sku", "available_quantity", "updated_at")
        read_only_fields = ("updated_at",)
