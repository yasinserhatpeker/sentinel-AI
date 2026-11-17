from datetime import timedelta

from django.utils import timezone
from rest_framework import serializers

from .models import Order


class OrderCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Order
        fields = ("reference", "amount")


class OrderSerializer(serializers.ModelSerializer):
    class Meta:
        model = Order
        fields = ("id", "reference", "amount", "status", "created_at")


class MetricSerializer(serializers.Serializer):
    name = serializers.RegexField(r"^[a-z][a-z0-9_.-]{0,127}$")
    value = serializers.FloatField()
    unit = serializers.RegexField(r"^[a-zA-Z0-9_./-]{1,32}$", required=False, allow_blank=False)


class TelemetryContextSerializer(serializers.Serializer):
    environment = serializers.ChoiceField(choices=("local",))
    service = serializers.RegexField(r"^[a-z][a-z0-9_.-]{0,95}$")
    instance = serializers.RegexField(r"^[a-zA-Z0-9_.-]{1,96}$")
    deployment_id = serializers.RegexField(
        r"^[a-zA-Z0-9_.-]{1,96}$", required=False, allow_blank=False
    )
    trace_id = serializers.RegexField(r"^[a-fA-F0-9]{16,32}$", required=False, allow_blank=False)


class TelemetryEventSerializer(serializers.Serializer):
    event_id = serializers.UUIDField()
    observed_at = serializers.DateTimeField()
    metric = MetricSerializer()
    context = TelemetryContextSerializer()
    dimensions = serializers.DictField(
        child=serializers.RegexField(r"^[a-zA-Z0-9_.-]{1,64}$"), required=False, default=dict
    )

    def validate_observed_at(self, value):
        now = timezone.now()
        if value < now - timedelta(days=7) or value > now + timedelta(minutes=5):
            raise serializers.ValidationError("telemetry_timestamp_out_of_range")
        return value

    def validate_dimensions(self, value):
        if len(value) > 10:
            raise serializers.ValidationError("telemetry_dimensions_limit_exceeded")
        if any(not key.replace("_", "").replace(".", "").replace("-", "").isalnum() for key in value):
            raise serializers.ValidationError("telemetry_dimension_key_invalid")
        return value


class TelemetryBatchSerializer(serializers.Serializer):
    schema_version = serializers.ChoiceField(choices=("telemetry.v1",))
    events = TelemetryEventSerializer(many=True, min_length=1, max_length=100)

    def validate_events(self, value):
        event_ids = [event["event_id"] for event in value]
        if len(event_ids) != len(set(event_ids)):
            raise serializers.ValidationError("telemetry_event_id_duplicate_in_batch")
        return value


class TelemetryServiceQuerySerializer(serializers.Serializer):
    environment = serializers.ChoiceField(choices=("local",))


class TelemetryAggregateQuerySerializer(serializers.Serializer):
    environment = serializers.ChoiceField(choices=("local",))
    service = serializers.RegexField(r"^[a-z][a-z0-9_.-]{0,95}$")
    start = serializers.DateTimeField()
    end = serializers.DateTimeField()

    def validate(self, attrs):
        start = attrs["start"]
        end = attrs["end"]
        if timezone.is_naive(start) or timezone.is_naive(end):
            raise serializers.ValidationError("telemetry_range_must_be_utc_aware")
        if end <= start:
            raise serializers.ValidationError("telemetry_range_invalid")
        if end - start > timedelta(hours=24):
            raise serializers.ValidationError("telemetry_range_exceeds_maximum")
        return attrs


class BoundedAnalysisQuerySerializer(serializers.Serializer):
    environment = serializers.ChoiceField(choices=("local",))
    service = serializers.RegexField(r"^[a-z][a-z0-9_.-]{0,95}$")
    start = serializers.DateTimeField()
    end = serializers.DateTimeField()
    limit = serializers.IntegerField(min_value=1, max_value=500, required=False, default=200)

    def validate(self, attrs):
        if attrs["end"] <= attrs["start"]:
            raise serializers.ValidationError("analysis_range_invalid")
        if attrs["end"] - attrs["start"] > timedelta(days=30):
            raise serializers.ValidationError("analysis_range_exceeds_maximum")
        return attrs


class LocalEnvironmentSerializer(serializers.Serializer):
    environment = serializers.ChoiceField(choices=("local",))


class ModelTrainSerializer(BoundedAnalysisQuerySerializer):
    minimum_samples = serializers.IntegerField(min_value=50, max_value=100000, required=False, default=50)
    contamination = serializers.FloatField(min_value=0.001, max_value=0.5, required=False, default=0.05)
    random_state = serializers.IntegerField(min_value=0, max_value=2147483647, required=False, default=42)


class LstmPrototypeTrainSerializer(BoundedAnalysisQuerySerializer):
    minimum_sequences = serializers.IntegerField(min_value=60, max_value=100000, required=False, default=60)
    sequence_length = serializers.IntegerField(min_value=12, max_value=288, required=False, default=12)
    epochs = serializers.IntegerField(min_value=1, max_value=200, required=False, default=25)
    seed = serializers.IntegerField(min_value=0, max_value=2147483647, required=False, default=42)


class FaultExperimentCreateSerializer(serializers.Serializer):
    environment = serializers.ChoiceField(choices=("local",))
    service = serializers.ChoiceField(choices=("orders-api", "payments-api", "inventory-api", "notifications-api", "reporting-worker"))
    fault_type = serializers.ChoiceField(choices=("high_latency", "error_burst", "database_slowdown", "queue_backlog"))
    duration_seconds = serializers.IntegerField(min_value=15, max_value=600)
    parameters = serializers.DictField(child=serializers.FloatField())
    seed = serializers.IntegerField(min_value=0, max_value=2147483647, required=False, default=42)

    def validate_parameters(self, value):
        if len(value) != 1:
            raise serializers.ValidationError("fault_parameters_invalid")
        return value

