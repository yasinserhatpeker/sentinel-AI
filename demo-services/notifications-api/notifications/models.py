from django.db import models


class Notification(models.Model):
    recipient_reference = models.CharField(max_length=48)
    channel = models.CharField(max_length=16, default="email")
    status = models.CharField(max_length=16, default="queued")
    created_at = models.DateTimeField(auto_now_add=True)
