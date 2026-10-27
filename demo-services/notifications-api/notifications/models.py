from django.db import models


class Notification(models.Model):
    workflow_key = models.CharField(max_length=96, unique=True, null=True, blank=True)
    recipient_reference = models.CharField(max_length=48)
    channel = models.CharField(max_length=16, default="email")
    status = models.CharField(max_length=16, default="queued")
    created_at = models.DateTimeField(auto_now_add=True)
