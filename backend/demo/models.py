import uuid

from django.db import models


class Order(models.Model):
    """Synthetic local-demo data; reset when the Docker volume is removed."""

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        REPORT_QUEUED = "report_queued", "Report queued"
        REPORT_READY = "report_ready", "Report ready"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    reference = models.CharField(max_length=64, unique=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=32, choices=Status.choices, default=Status.PENDING)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-created_at",)

