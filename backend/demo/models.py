import uuid

from django.conf import settings
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
    """Five-minute aggregate-only ML feature vector retained in the local database.

    ``feature_values`` is empty for the preserved ``features.v1`` contract.  Newer
    schemas use a fixed, versioned key allowlist rather than arbitrary telemetry
    dimensions, keeping dependency and time-series context bounded.
    """

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
    feature_values = models.JSONField(default=dict, blank=True)
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


class DetectionDecision(models.Model):
    """Traceable detector output retained with local derived telemetry."""

    class Severity(models.TextChoices):
        NORMAL = "normal", "Normal"
        WARNING = "warning", "Warning"
        CRITICAL = "critical", "Critical"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    feature = models.ForeignKey(TelemetryFeature, on_delete=models.PROTECT, related_name="detection_decisions")
    environment = models.CharField(max_length=32)
    service = models.CharField(max_length=96)
    detector_type = models.CharField(max_length=32)
    detector_version = models.CharField(max_length=32)
    configuration_version = models.CharField(max_length=64)
    model_version = models.CharField(max_length=64, blank=True)
    score = models.FloatField(null=True, blank=True)
    normalized_score = models.FloatField(null=True, blank=True)
    threshold = models.FloatField(null=True, blank=True)
    is_anomaly = models.BooleanField(default=False)
    severity = models.CharField(max_length=16, choices=Severity.choices, default=Severity.NORMAL)
    reasons = models.JSONField(default=list)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=(
                    "feature",
                    "detector_type",
                    "detector_version",
                    "configuration_version",
                    "model_version",
                ),
                name="unique_detector_decision_identity",
            ),
        ]
        indexes = [
            models.Index(fields=("environment", "service", "created_at")),
            models.Index(fields=("is_anomaly", "created_at")),
        ]


class DetectorModel(models.Model):
    """Versioned local model metadata; binary artifacts live outside source control."""

    class Status(models.TextChoices):
        TRAINED = "trained", "Trained"
        ACTIVE = "active", "Active"
        RETIRED = "retired", "Retired"
        FAILED = "failed", "Failed"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    model_version = models.CharField(max_length=64, unique=True)
    detector_type = models.CharField(max_length=32, default="isolation_forest")
    detector_version = models.CharField(max_length=32)
    feature_schema_version = models.CharField(max_length=32, default="features.v2")
    environment = models.CharField(max_length=32)
    service = models.CharField(max_length=96)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.TRAINED)
    configuration = models.JSONField(default=dict)
    feature_names = models.JSONField(default=list)
    sample_count = models.PositiveIntegerField()
    trained_from = models.DateTimeField()
    trained_until = models.DateTimeField()
    artifact_path = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    activated_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=("environment", "service", "status")),
            models.Index(fields=("detector_type", "created_at")),
        ]


class FaultExperiment(models.Model):
    """Audited, bounded local fault lifecycle retained for reproducible experiments."""

    class FaultType(models.TextChoices):
        HIGH_LATENCY = "high_latency", "High latency"
        ERROR_BURST = "error_burst", "Error burst"
        DATABASE_SLOWDOWN = "database_slowdown", "Database slowdown"
        QUEUE_BACKLOG = "queue_backlog", "Queue backlog"

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        ACTIVE = "active", "Active"
        RECOVERING = "recovering", "Recovering"
        COMPLETED = "completed", "Completed"
        STOPPED = "stopped", "Stopped"
        FAILED = "failed", "Failed"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    environment = models.CharField(max_length=32, default="local")
    service = models.CharField(max_length=96)
    fault_type = models.CharField(max_length=32, choices=FaultType.choices)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.PENDING)
    parameters = models.JSONField(default=dict)
    duration_seconds = models.PositiveSmallIntegerField()
    seed = models.PositiveIntegerField()
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="fault_experiments")
    repeated_from = models.ForeignKey("self", null=True, blank=True, on_delete=models.SET_NULL)
    created_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    stopped_at = models.DateTimeField(null=True, blank=True)
    recovery_until = models.DateTimeField(null=True, blank=True)
    failure_reason = models.CharField(max_length=96, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=("environment", "service", "status")),
            models.Index(fields=("expires_at", "status")),
        ]


class GroundTruthWindow(models.Model):
    """Synthetic experiment labels retained with derived local telemetry."""

    class Label(models.TextChoices):
        NORMAL = "normal", "Normal"
        FAULT_ACTIVE = "fault_active", "Fault active"
        RECOVERING = "recovering", "Recovering"

    experiment = models.ForeignKey(FaultExperiment, on_delete=models.CASCADE, related_name="ground_truth_windows")
    environment = models.CharField(max_length=32, default="local")
    service = models.CharField(max_length=96)
    window_start = models.DateTimeField()
    label = models.CharField(max_length=16, choices=Label.choices)
    fault_severity = models.FloatField()
    materialized_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("experiment", "service", "window_start"),
                name="unique_ground_truth_experiment_window",
            ),
        ]
        indexes = [models.Index(fields=("environment", "service", "window_start"))]


class DetectorEvaluation(models.Model):
    """Reproducible detector quality metrics for one bounded local experiment."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    experiment = models.ForeignKey(FaultExperiment, on_delete=models.CASCADE, related_name="evaluations")
    detector_type = models.CharField(max_length=32)
    detector_version = models.CharField(max_length=32)
    configuration_version = models.CharField(max_length=64)
    model_version = models.CharField(max_length=64, blank=True)
    true_positive = models.PositiveIntegerField(default=0)
    false_positive = models.PositiveIntegerField(default=0)
    true_negative = models.PositiveIntegerField(default=0)
    false_negative = models.PositiveIntegerField(default=0)
    precision = models.FloatField()
    recall = models.FloatField()
    f1_score = models.FloatField()
    false_positive_rate = models.FloatField()
    detection_delay_seconds = models.FloatField(null=True, blank=True)
    recovery_delay_seconds = models.FloatField(null=True, blank=True)
    evaluated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("experiment", "detector_type", "detector_version", "configuration_version", "model_version"),
                name="unique_detector_evaluation_identity",
            ),
        ]


class SequenceJournal(models.Model):
    """LSTM-ready ordered feature references; source feature values are not duplicated."""

    class Split(models.TextChoices):
        TRAIN = "train", "Train"
        VALIDATION = "validation", "Validation"
        TEST = "test", "Test"

    schema_version = models.CharField(max_length=32, default="sequence.v1")
    environment = models.CharField(max_length=32)
    service = models.CharField(max_length=96)
    window_end = models.DateTimeField()
    sequence_length = models.PositiveSmallIntegerField(default=12)
    feature_ids = models.JSONField(default=list)
    target_is_anomaly = models.BooleanField(default=False)
    split = models.CharField(max_length=16, choices=Split.choices)
    materialized_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("schema_version", "environment", "service", "window_end"),
                name="unique_sequence_journal_window",
            ),
        ]
        indexes = [models.Index(fields=("environment", "service", "split", "window_end"))]

