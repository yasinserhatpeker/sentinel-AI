from django.db import models


class Order(models.Model):
    reference = models.CharField(max_length=48, unique=True)
    total = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=16, default="created")
    created_at = models.DateTimeField(auto_now_add=True)
