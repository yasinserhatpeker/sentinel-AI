from django.core.cache import cache
from django.db.models import QuerySet
from rest_framework import permissions, status
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.authentication import JWTAuthentication

from .machine_authentication import DemoTelemetryTokenAuthentication
from .exceptions import AnalysisReadinessConflict
from .detection.base import normalize_positive_score, normalize_signed_score
from .detection.isolation_forest import activate_model, train_isolation_forest
from .detection.readiness import model_data_readiness
from .detection.sequences import materialize_sequence_journals, train_lstm_prototype
from .faults import repeat_experiment, start_experiment, stop_experiment
from .models import DetectionDecision, DetectorEvaluation, DetectorModel, FaultExperiment, Order, TelemetryAggregate
from .serializers import (
    BoundedAnalysisQuerySerializer,
    FaultExperimentCreateSerializer,
    LocalEnvironmentSerializer,
    LstmPrototypeTrainSerializer,
    ModelTrainSerializer,
    OrderCreateSerializer,
    OrderSerializer,
    TelemetryAggregateQuerySerializer,
    TelemetryBatchSerializer,
    TelemetryServiceQuerySerializer,
)
from .tasks import generate_order_report
from .telemetry import record_report_task_enqueued
from .telemetry_ingestion import aggregate_minute, persist_metric_events


class IsSuperUser(permissions.BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.is_active and request.user.is_superuser)


def _decision_data(decision: DetectionDecision, *, detail: bool = False) -> dict:
    normalized_score = _normalized_decision_score(decision)
    data = {
        "id": str(decision.pk), "environment": decision.environment, "service": decision.service,
        "window_start": decision.feature.window_start, "detector_type": decision.detector_type,
        "detector_version": decision.detector_version, "configuration_version": decision.configuration_version,
        "model_version": decision.model_version or None, "score": normalized_score,
        "threshold": 0.5 if normalized_score is not None else None,
        "raw_score": decision.score, "raw_threshold": decision.threshold,
        "is_anomaly": decision.is_anomaly, "severity": decision.severity, "reasons": decision.reasons,
    }
    if detail:
        data["evidence"] = {
            "feature_id": decision.feature_id, "feature_schema_version": decision.feature.schema_version,
            "request_count": decision.feature.request_count, "error_rate": decision.feature.error_rate,
            "latency_p95_ms": decision.feature.latency_p95_ms, "cpu_average": decision.feature.cpu_average,
            "db_query_p95_ms": decision.feature.db_query_p95_ms, "queue_depth_max": decision.feature.queue_depth_max,
        }
    return data


def _normalized_decision_score(decision: DetectionDecision) -> float | None:
    if decision.normalized_score is not None:
        return decision.normalized_score
    if decision.detector_type == "isolation_forest":
        return normalize_signed_score(decision.score)
    return normalize_positive_score(decision.score, decision.threshold)


def _model_data(model: DetectorModel) -> dict:
    return {
        "id": str(model.pk), "model_version": model.model_version, "detector_type": model.detector_type,
        "detector_version": model.detector_version, "feature_schema_version": model.feature_schema_version,
        "environment": model.environment, "service": model.service, "status": model.status,
        "configuration": model.configuration, "feature_count": len(model.feature_names),
        "sample_count": model.sample_count, "trained_from": model.trained_from,
        "trained_until": model.trained_until, "created_at": model.created_at, "activated_at": model.activated_at,
        "artifact_available": bool(model.artifact_path),
    }


def _experiment_data(experiment: FaultExperiment) -> dict:
    return {
        "id": str(experiment.pk), "environment": experiment.environment, "service": experiment.service,
        "fault_type": experiment.fault_type, "status": experiment.status, "parameters": experiment.parameters,
        "duration_seconds": experiment.duration_seconds, "seed": experiment.seed,
        "created_by": experiment.created_by_id, "repeated_from": str(experiment.repeated_from_id) if experiment.repeated_from_id else None,
        "created_at": experiment.created_at, "started_at": experiment.started_at, "expires_at": experiment.expires_at,
        "stopped_at": experiment.stopped_at, "recovery_until": experiment.recovery_until,
        "failure_reason": experiment.failure_reason or None,
    }


class HealthView(APIView):
    authentication_classes = []
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        return Response({"status": "ok"})


class OrderCreateView(APIView):
    def post(self, request):
        serializer = OrderCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        order = serializer.save(status=Order.Status.REPORT_QUEUED)
        cache.set(f"demo-order:{order.id}", order.reference, timeout=300)
        task = generate_order_report.delay(str(order.id))
        record_report_task_enqueued()
        return Response(
            {"order": OrderSerializer(order).data, "report_task_id": task.id},
            status=status.HTTP_201_CREATED,
        )


class TelemetryIngestView(APIView):
    # Browser users retain JWT access; local demo containers use a secret-derived signature.
    authentication_classes = [DemoTelemetryTokenAuthentication, JWTAuthentication]

    def post(self, request):
        serializer = TelemetryBatchSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        events = serializer.validated_data["events"]
        inserted, duplicates = persist_metric_events(events)
        # Keep the local dashboard responsive after a genuine service request.
        # The periodic task still recomputes completed windows; this upsert only
        # exposes the in-progress minute sooner and never fabricates a value.
        for window in {event["observed_at"].replace(second=0, microsecond=0) for event in events}:
            aggregate_minute(window)
        return Response(
            {
                "schema_version": serializer.validated_data["schema_version"],
                "accepted": inserted,
                "duplicates": duplicates,
            },
            status=status.HTTP_202_ACCEPTED,
        )


class TelemetryServiceListView(APIView):
    """Expose locally available aggregate services for an explicit environment."""

    def get(self, request):
        serializer = TelemetryServiceQuerySerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        services = (
            TelemetryAggregate.objects.filter(environment=serializer.validated_data["environment"])
            .order_by("service")
            .values_list("service", flat=True)
            .distinct()
        )
        return Response({"environment": serializer.validated_data["environment"], "services": list(services)})


class SystemOverviewView(APIView):
    """Aggregate-only local system health; unavailable analysis is never reported as zero."""

    def get(self, request):
        serializer = TelemetryServiceQuerySerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        environment = serializer.validated_data["environment"]
        services = list(TelemetryAggregate.objects.filter(environment=environment).order_by("service").values_list("service", flat=True).distinct())
        summary = []
        for service in services:
            latest = {row.metric_name: row for row in TelemetryAggregate.objects.filter(environment=environment, service=service).order_by("metric_name", "-window_start").distinct("metric_name")}
            error_rate = latest.get("http.server.error_rate")
            latency = latest.get("http.server.duration")
            queue = latest.get("queue.depth")
            status_value = "degraded" if error_rate and error_rate.last_value > 0 else "healthy"
            summary.append({"service": service, "status": status_value, "p95_latency_ms": latency.p95 if latency else None, "queue_depth": queue.last_value if queue else None})
        slowest_item = max((item for item in summary if item["p95_latency_ms"] is not None), key=lambda item: item["p95_latency_ms"], default=None)
        busiest_item = max((item for item in summary if item["queue_depth"] is not None), key=lambda item: item["queue_depth"], default=None)
        slowest = ({"service": slowest_item["service"], "p95_latency_ms": slowest_item["p95_latency_ms"]} if slowest_item else None)
        busiest = ({"service": busiest_item["service"], "queue_depth": busiest_item["queue_depth"]} if busiest_item else None)
        anomaly_candidates = list(DetectionDecision.objects.filter(environment=environment, is_anomaly=True).select_related("feature").order_by("-created_at")[:500])
        anomaly = max(anomaly_candidates, key=lambda item: _normalized_decision_score(item) or 0.0, default=None)
        active_faults = list(FaultExperiment.objects.filter(environment=environment, status__in=(FaultExperiment.Status.PENDING, FaultExperiment.Status.ACTIVE)).order_by("-created_at")[:10])
        recovering_faults = list(FaultExperiment.objects.filter(environment=environment, status=FaultExperiment.Status.RECOVERING).order_by("-created_at")[:10])
        latest_completed_fault = FaultExperiment.objects.filter(environment=environment, status=FaultExperiment.Status.COMPLETED).order_by("-created_at").first()
        current_fault = (active_faults or recovering_faults or [None])[0]
        return Response({"schema_version": "overview.v2", "environment": environment, "services": summary, "healthy_service_count": sum(item["status"] == "healthy" for item in summary), "degraded_service_count": sum(item["status"] == "degraded" for item in summary), "slowest_service": slowest, "busiest_queue": busiest, "open_incidents": None, "highest_anomaly_score": ({"service": anomaly.service, "score": _normalized_decision_score(anomaly), "raw_score": anomaly.score, "severity": anomaly.severity} if anomaly else None), "active_fault_count": len(active_faults), "recovering_fault_count": len(recovering_faults), "active_faults": [_experiment_data(item) for item in active_faults], "recovering_faults": [_experiment_data(item) for item in recovering_faults], "fault_context_available": bool(current_fault or latest_completed_fault), "latest_fault": (_experiment_data(current_fault) if current_fault else None), "latest_completed_fault": (_experiment_data(latest_completed_fault) if latest_completed_fault else None), "dependencies": [["orders-api", "payments-api"], ["payments-api", "inventory-api"], ["inventory-api", "notifications-api"], ["notifications-api", "reporting-worker"]]})


class TelemetryAggregateListView(APIView):
    """Return bounded aggregate telemetry without disclosing raw events or dimensions."""

    def get(self, request):
        serializer = TelemetryAggregateQuerySerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        scope = serializer.validated_data
        aggregates: QuerySet[TelemetryAggregate] = TelemetryAggregate.objects.filter(
            environment=scope["environment"],
            service=scope["service"],
            window_start__gte=scope["start"],
            window_start__lt=scope["end"],
        ).order_by("window_start", "metric_name", "instance")

        if not TelemetryAggregate.objects.filter(
            environment=scope["environment"], service=scope["service"]
        ).exists():
            raise NotFound("telemetry_service_not_found")

        points = [
            {
                "timestamp": aggregate.window_start,
                "metric": aggregate.metric_name,
                "unit": aggregate.unit,
                "count": aggregate.event_count,
                "minimum": aggregate.minimum,
                "maximum": aggregate.maximum,
                "average": aggregate.average,
                "last": aggregate.last_value,
                "p50": aggregate.p50,
                "p95": aggregate.p95,
                "p99": aggregate.p99,
            }
            for aggregate in aggregates
        ]
        metrics = {point["metric"] for point in points}
        groups = {
            "http": {"http.server.request_count", "http.server.error_rate", "http.server.duration"},
            "runtime": {"runtime.cpu.usage", "runtime.memory.usage"},
            "database": {"db.connection.usage", "db.query.duration"},
            "queue": {
                "queue.depth",
                "queue.oldest_message_age",
                "queue.enqueue_rate",
                "queue.dequeue_rate",
                "queue.failed_task_count",
            },
        }
        availability = {name: bool(required & metrics) for name, required in groups.items()}
        return Response(
            {
                "schema_version": "telemetry.v1",
                "scope": {
                    "environment": scope["environment"],
                    "service": scope["service"],
                    "start": scope["start"],
                    "end": scope["end"],
                },
                "availability": availability,
                "points": points,
            }
        )


class AnomalyListView(APIView):
    permission_classes = [IsSuperUser]

    def get(self, request):
        serializer = BoundedAnalysisQuerySerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        scope = serializer.validated_data
        queryset = DetectionDecision.objects.filter(
            environment=scope["environment"], service=scope["service"], is_anomaly=True,
            feature__window_start__gte=scope["start"], feature__window_start__lt=scope["end"],
        ).select_related("feature").order_by("-feature__window_start", "detector_type")[:scope["limit"]]
        return Response({"schema_version": "anomalies.v1", "scope": {key: scope[key] for key in ("environment", "service", "start", "end")}, "results": [_decision_data(item) for item in queryset]})


class AnomalyDetailView(APIView):
    permission_classes = [IsSuperUser]

    def get(self, request, anomaly_id):
        serializer = LocalEnvironmentSerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        try:
            decision = DetectionDecision.objects.select_related("feature").get(pk=anomaly_id, environment=serializer.validated_data["environment"], is_anomaly=True)
        except DetectionDecision.DoesNotExist as error:
            raise NotFound("anomaly_not_found") from error
        return Response({"schema_version": "anomalies.v1", "anomaly": _decision_data(decision, detail=True)})


class ModelListView(APIView):
    permission_classes = [IsSuperUser]

    def get(self, request):
        serializer = BoundedAnalysisQuerySerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        scope = serializer.validated_data
        models = DetectorModel.objects.filter(environment=scope["environment"], service=scope["service"], created_at__gte=scope["start"], created_at__lt=scope["end"]).order_by("-created_at")[:scope["limit"]]
        return Response({"schema_version": "models.v1", "results": [_model_data(model) for model in models]})


class ModelReadinessView(APIView):
    permission_classes = [IsSuperUser]

    def get(self, request):
        serializer = BoundedAnalysisQuerySerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        scope = serializer.validated_data
        return Response(model_data_readiness(
            environment=scope["environment"],
            service=scope["service"],
            start=scope["start"],
            end=scope["end"],
        ))


class ModelTrainView(APIView):
    permission_classes = [IsSuperUser]

    def post(self, request):
        serializer = ModelTrainSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        try:
            model = train_isolation_forest(environment=data["environment"], service=data["service"], start=data["start"], end=data["end"], minimum_samples=data["minimum_samples"], contamination=data["contamination"], random_state=data["random_state"])
        except ValueError as error:
            if str(error) == "model_training_insufficient_samples":
                raise AnalysisReadinessConflict(str(error)) from error
            raise ValidationError(str(error)) from error
        return Response({"schema_version": "models.v1", "model": _model_data(model)}, status=status.HTTP_201_CREATED)


class ModelActivateView(APIView):
    permission_classes = [IsSuperUser]

    def post(self, request, model_id):
        serializer = LocalEnvironmentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            model = DetectorModel.objects.get(pk=model_id, environment=serializer.validated_data["environment"])
        except DetectorModel.DoesNotExist as error:
            raise NotFound("model_not_found") from error
        try:
            model = activate_model(model)
        except ValueError as error:
            raise ValidationError(str(error)) from error
        return Response({"schema_version": "models.v1", "model": _model_data(model)})


class LstmPrototypeTrainView(APIView):
    """Run the gated offline prototype explicitly; it never activates a live model."""

    permission_classes = [IsSuperUser]

    def post(self, request):
        serializer = LstmPrototypeTrainSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        try:
            materialized = materialize_sequence_journals(
                environment=data["environment"], service=data["service"],
                sequence_length=data["sequence_length"], start=data["start"], end=data["end"],
            )
            result = train_lstm_prototype(
                environment=data["environment"], service=data["service"],
                minimum_sequences=data["minimum_sequences"], epochs=data["epochs"], seed=data["seed"],
                start=data["start"], end=data["end"],
            )
        except ValueError as error:
            if str(error) in {"lstm_minimum_sequences_not_met", "lstm_split_incomplete"}:
                raise AnalysisReadinessConflict(str(error)) from error
            raise ValidationError(str(error)) from error
        return Response({
            "schema_version": "lstm-prototype-result.v1",
            "environment": data["environment"], "service": data["service"],
            "materialized_sequence_count": materialized,
            "sequence_length": data["sequence_length"], "epochs": data["epochs"], "seed": data["seed"],
            "train_samples": result.train_samples, "validation_samples": result.validation_samples,
            "test_samples": result.test_samples, "validation_accuracy": result.validation_accuracy,
            "test_accuracy": result.test_accuracy, "activated": False,
        })


class FaultExperimentListCreateView(APIView):
    permission_classes = [IsSuperUser]

    def get(self, request):
        serializer = BoundedAnalysisQuerySerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        scope = serializer.validated_data
        experiments = FaultExperiment.objects.filter(environment=scope["environment"], service=scope["service"], created_at__gte=scope["start"], created_at__lt=scope["end"]).select_related("created_by", "repeated_from").order_by("-created_at")[:scope["limit"]]
        return Response({"schema_version": "fault-experiments.v1", "results": [_experiment_data(item) for item in experiments]})

    def post(self, request):
        serializer = FaultExperimentCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        try:
            experiment = start_experiment(actor=request.user, service=data["service"], fault_type=data["fault_type"], duration_seconds=data["duration_seconds"], parameters=data["parameters"], seed=data["seed"])
        except PermissionError as error:
            raise PermissionDenied(str(error)) from error
        except ValueError as error:
            raise ValidationError(str(error)) from error
        return Response({"schema_version": "fault-experiments.v1", "experiment": _experiment_data(experiment)}, status=status.HTTP_201_CREATED)


class FaultExperimentActionView(APIView):
    permission_classes = [IsSuperUser]
    action = ""

    def post(self, request, experiment_id):
        serializer = LocalEnvironmentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            experiment = FaultExperiment.objects.get(pk=experiment_id, environment=serializer.validated_data["environment"])
        except FaultExperiment.DoesNotExist as error:
            raise NotFound("fault_experiment_not_found") from error
        try:
            result = stop_experiment(experiment) if self.action == "stop" else repeat_experiment(experiment, actor=request.user)
        except (ValueError, RuntimeError) as error:
            raise ValidationError(str(error)) from error
        return Response({"schema_version": "fault-experiments.v1", "experiment": _experiment_data(result)})


class FaultExperimentStopView(FaultExperimentActionView):
    action = "stop"


class FaultExperimentRepeatView(FaultExperimentActionView):
    action = "repeat"


class EvaluationListView(APIView):
    permission_classes = [IsSuperUser]

    def get(self, request):
        serializer = BoundedAnalysisQuerySerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        scope = serializer.validated_data
        evaluations = DetectorEvaluation.objects.filter(experiment__environment=scope["environment"], experiment__service=scope["service"], evaluated_at__gte=scope["start"], evaluated_at__lt=scope["end"]).select_related("experiment").order_by("-evaluated_at")[:scope["limit"]]
        results = [{"id": str(item.pk), "experiment_id": str(item.experiment_id), "detector_type": item.detector_type, "detector_version": item.detector_version, "configuration_version": item.configuration_version, "model_version": item.model_version or None, "confusion": {"true_positive": item.true_positive, "false_positive": item.false_positive, "true_negative": item.true_negative, "false_negative": item.false_negative}, "precision": item.precision, "recall": item.recall, "f1_score": item.f1_score, "false_positive_rate": item.false_positive_rate, "detection_delay_seconds": item.detection_delay_seconds, "recovery_delay_seconds": item.recovery_delay_seconds, "evaluated_at": item.evaluated_at} for item in evaluations]
        return Response({"schema_version": "evaluations.v1", "results": results})
