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


class TelemetryEvent(models.Model):
    """Local synthetic raw metric telemetry, retained for 30 days."""

    event_id = models.UUIDField(primary_key=True, editable=False)
    schema_version = models.CharField(max_length=32)
    observed_at = models.DateTimeField()
    ingested_at = models.DateTimeField(auto_now_add=True)
    environment = models.CharField(max_length=32)
    service = models.CharField(max_length=96)
    instance = models.CharField(max_length=96)
    deployment_id = models.CharField(max_length=96, blank=True)
    trace_id = models.CharField(max_length=64, blank=True)
    metric_name = models.CharField(max_length=128)
    metric_value = models.FloatField()
    unit = models.CharField(max_length=32, blank=True)
    dimensions = models.JSONField(default=dict)
    dimensions_fingerprint = models.CharField(max_length=64)

    class Meta:
        ordering = ("observed_at", "event_id")
        indexes = [
            models.Index(fields=("observed_at", "environment", "service", "metric_name")),
        ]


class TelemetryAggregate(models.Model):
    """One-minute local telemetry summary derived from raw metric events."""

    window_start = models.DateTimeField()
    environment = models.CharField(max_length=32)
    service = models.CharField(max_length=96)
    instance = models.CharField(max_length=96)
    deployment_id = models.CharField(max_length=96, blank=True)
    metric_name = models.CharField(max_length=128)
    unit = models.CharField(max_length=32, blank=True)
    dimensions_fingerprint = models.CharField(max_length=64)
    event_count = models.PositiveIntegerField()
    minimum = models.FloatField()
    maximum = models.FloatField()
    average = models.FloatField()
    last_value = models.FloatField()
    p50 = models.FloatField()
    p95 = models.FloatField()
    p99 = models.FloatField()
    calculated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=(
                    "window_start",
                    "environment",
                    "service",
                    "instance",
                    "deployment_id",
                    "metric_name",
                    "unit",
                    "dimensions_fingerprint",
                ),
                name="unique_telemetry_aggregate_window_scope",
            ),
        ]
        indexes = [
            models.Index(fields=("window_start", "environment", "service", "metric_name")),
        ]


class TelemetryFeature(models.Model):
    """Five-minute, aggregate-only ML feature vector for a service."""

    schema_version = models.CharField(max_length=32, default="features.v1")
    window_start = models.DateTimeField()
    environment = models.CharField(max_length=32)
    service = models.CharField(max_length=96)
    source_window_count = models.PositiveSmallIntegerField(default=0)
    request_count = models.FloatField(null=True, blank=True)
    error_rate = models.FloatField(null=True, blank=True)
    latency_p95_ms = models.FloatField(null=True, blank=True)
    cpu_average = models.FloatField(null=True, blank=True)
    memory_average_mb = models.FloatField(null=True, blank=True)
    db_query_p95_ms = models.FloatField(null=True, blank=True)
    queue_depth_max = models.FloatField(null=True, blank=True)
    queue_oldest_age_max_seconds = models.FloatField(null=True, blank=True)
    queue_enqueue_count = models.FloatField(null=True, blank=True)
    queue_dequeue_count = models.FloatField(null=True, blank=True)
    failed_task_count = models.FloatField(null=True, blank=True)
    materialized_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("schema_version", "window_start", "environment", "service"),
                name="unique_telemetry_feature_window_scope",
            ),
        ]
        indexes = [
            models.Index(fields=("window_start", "environment", "service")),
        ]

