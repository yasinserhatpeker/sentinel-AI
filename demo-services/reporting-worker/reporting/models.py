from django.db import models


class ReportJob(models.Model):
    report_type = models.CharField(max_length=32)
    status = models.CharField(max_length=16, default="queued")
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
