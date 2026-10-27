from django.db import models


class PaymentAuthorization(models.Model):
    reference = models.CharField(max_length=48, unique=True)
    order_reference = models.CharField(max_length=48)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=16, default="authorized")
    created_at = models.DateTimeField(auto_now_add=True)
