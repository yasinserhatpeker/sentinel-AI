from django.db import models


class StockItem(models.Model):
    sku = models.CharField(max_length=48, unique=True)
    available_quantity = models.PositiveIntegerField(default=0)
    updated_at = models.DateTimeField(auto_now=True)


class InventoryReservation(models.Model):
    """One reservation per order reference makes workflow retries idempotent."""

    order_reference = models.CharField(max_length=64, unique=True)
    sku = models.CharField(max_length=64)
    quantity = models.PositiveIntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)
