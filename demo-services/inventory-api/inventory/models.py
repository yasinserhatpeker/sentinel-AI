from django.db import models


class StockItem(models.Model):
    sku = models.CharField(max_length=48, unique=True)
    available_quantity = models.PositiveIntegerField(default=0)
    updated_at = models.DateTimeField(auto_now=True)
