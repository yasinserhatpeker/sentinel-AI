from rest_framework import serializers
from .models import ReportJob


class ReportJobSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReportJob
        fields = ("id", "report_type", "status", "created_at", "completed_at")
        read_only_fields = ("id", "status", "created_at", "completed_at")
