"""Bounded local fault orchestration and ground-truth materialization."""

from __future__ import annotations

import hashlib
import hmac
import json
import time
import urllib.error
import urllib.request
from datetime import timedelta

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from .models import FaultExperiment, GroundTruthWindow
from .telemetry_ingestion import feature_window_start


SERVICE_URLS = {
    "orders-api": "http://orders-api:8080",
    "payments-api": "http://payments-api:8080",
    "inventory-api": "http://inventory-api:8080",
    "notifications-api": "http://notifications-api:8080",
    "reporting-worker": "http://reporting-worker:8080",
}
SCENARIO_NAMES = {
    FaultExperiment.FaultType.HIGH_LATENCY: "latency",
    FaultExperiment.FaultType.ERROR_BURST: "errors",
    FaultExperiment.FaultType.DATABASE_SLOWDOWN: "database-slowdown",
    FaultExperiment.FaultType.QUEUE_BACKLOG: "queue-backlog",
}
ACTIVE_STATUSES = (FaultExperiment.Status.PENDING, FaultExperiment.Status.ACTIVE, FaultExperiment.Status.RECOVERING)
RECOVERY_SECONDS = 120


def complete_expired_recoveries(*, now=None, environment: str = "local", service: str | None = None) -> int:
    """Complete elapsed recovery records even when the Celery watchdog is unavailable."""

    current = now or timezone.now()
    queryset = FaultExperiment.objects.filter(
        environment=environment,
        status=FaultExperiment.Status.RECOVERING,
        recovery_until__lte=current,
    )
    if service is not None:
        queryset = queryset.filter(service=service)
    return queryset.update(status=FaultExperiment.Status.COMPLETED)


def validate_experiment(service: str, fault_type: str, duration_seconds: int, parameters: dict) -> dict:
    if service not in SERVICE_URLS:
        raise ValueError("fault_service_not_allowed")
    if fault_type not in SCENARIO_NAMES:
        raise ValueError("fault_type_not_allowed")
    if fault_type == FaultExperiment.FaultType.QUEUE_BACKLOG and service != "reporting-worker":
        raise ValueError("queue_backlog_requires_reporting_worker")
    if not 15 <= duration_seconds <= 600:
        raise ValueError("fault_duration_out_of_range")
    allowed = {
        FaultExperiment.FaultType.HIGH_LATENCY: {"delay_ms"},
        FaultExperiment.FaultType.ERROR_BURST: {"error_probability"},
        FaultExperiment.FaultType.DATABASE_SLOWDOWN: {"delay_ms"},
        FaultExperiment.FaultType.QUEUE_BACKLOG: {"delay_ms"},
    }[fault_type]
    if set(parameters) != allowed:
        raise ValueError("fault_parameters_invalid")
    normalized = {key: float(value) for key, value in parameters.items()}
    if "delay_ms" in normalized and not 50 <= normalized["delay_ms"] <= 5000:
        raise ValueError("fault_delay_out_of_range")
    if "error_probability" in normalized and not 0.05 <= normalized["error_probability"] <= 1.0:
        raise ValueError("fault_probability_out_of_range")
    return normalized


def _send_control(service: str, payload: dict) -> dict:
    body = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    timestamp = str(int(time.time()))
    message = b"sentinelai-fault-control-v1." + timestamp.encode() + b"." + body
    signature = hmac.new(settings.SECRET_KEY.encode(), message, hashlib.sha256).hexdigest()
    request = urllib.request.Request(
        f"{SERVICE_URLS[service]}/_internal/fault-control/",
        data=body,
        headers={"Content-Type": "application/json", "X-Fault-Timestamp": timestamp, "X-Fault-Signature": signature},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=3) as response:
            return json.loads(response.read())
    except (OSError, urllib.error.HTTPError, json.JSONDecodeError) as error:
        raise RuntimeError("fault_control_unavailable") from error


@transaction.atomic
def start_experiment(*, actor, service: str, fault_type: str, duration_seconds: int, parameters: dict, seed: int, repeated_from=None) -> FaultExperiment:
    if not actor.is_active or not actor.is_superuser:
        raise PermissionError("fault_super_admin_required")
    if not 0 <= seed <= 2_147_483_647:
        raise ValueError("fault_seed_out_of_range")
    normalized = validate_experiment(service, fault_type, duration_seconds, parameters)
    complete_expired_recoveries(service=service)
    if FaultExperiment.objects.select_for_update().filter(environment="local", service=service, status__in=ACTIVE_STATUSES).exists():
        raise ValueError("fault_experiment_conflict")
    experiment = FaultExperiment.objects.create(
        environment="local", service=service, fault_type=fault_type, parameters=normalized,
        duration_seconds=duration_seconds, seed=seed, created_by=actor, repeated_from=repeated_from,
    )
    now = timezone.now()
    payload = {"action": "start", "scenario": SCENARIO_NAMES[fault_type], "duration_seconds": duration_seconds, "experiment_id": str(experiment.pk), "seed": seed, "parameters": normalized}
    try:
        _send_control(service, payload)
    except RuntimeError as error:
        experiment.status = FaultExperiment.Status.FAILED
        experiment.failure_reason = str(error)
        experiment.save(update_fields=("status", "failure_reason"))
        return experiment
    experiment.status = FaultExperiment.Status.ACTIVE
    experiment.started_at = now
    experiment.expires_at = now + timedelta(seconds=duration_seconds)
    experiment.save(update_fields=("status", "started_at", "expires_at"))
    return experiment


def _fault_severity(experiment: FaultExperiment) -> float:
    if "error_probability" in experiment.parameters:
        return float(experiment.parameters["error_probability"])
    return min(1.0, float(experiment.parameters.get("delay_ms", 0)) / 5000)


def materialize_ground_truth(experiment: FaultExperiment) -> int:
    if experiment.started_at is None or experiment.recovery_until is None:
        return 0
    active_until = experiment.stopped_at or experiment.expires_at or experiment.started_at
    active_duration_seconds = max(0.0, (active_until - experiment.started_at).total_seconds())
    minimum_active_overlap_seconds = min(30.0, active_duration_seconds / 2.0)
    start = feature_window_start(experiment.started_at - timedelta(minutes=10))
    end = feature_window_start(experiment.recovery_until + timedelta(minutes=5))
    count = 0
    cursor = start
    while cursor <= end:
        window_end = cursor + timedelta(minutes=5)
        active_overlap_seconds = max(
            0.0,
            (min(window_end, active_until) - max(cursor, experiment.started_at)).total_seconds(),
        )
        if active_overlap_seconds > 0 and active_overlap_seconds >= minimum_active_overlap_seconds:
            label = GroundTruthWindow.Label.FAULT_ACTIVE
        elif cursor < experiment.started_at:
            # A feature window that contains only a few trailing fault seconds
            # is predominantly normal and should not count as a model miss.
            label = GroundTruthWindow.Label.NORMAL
        else:
            label = GroundTruthWindow.Label.RECOVERING
        GroundTruthWindow.objects.update_or_create(
            experiment=experiment, service=experiment.service, window_start=cursor,
            defaults={"environment": "local", "label": label, "fault_severity": _fault_severity(experiment)},
        )
        count += 1
        cursor += timedelta(minutes=5)
    return count


@transaction.atomic
def stop_experiment(experiment: FaultExperiment, *, now=None) -> FaultExperiment:
    locked = FaultExperiment.objects.select_for_update().get(pk=experiment.pk)
    if locked.status in (FaultExperiment.Status.RECOVERING, FaultExperiment.Status.COMPLETED, FaultExperiment.Status.STOPPED, FaultExperiment.Status.FAILED):
        return locked
    current = now or timezone.now()
    _send_control(locked.service, {"action": "stop", "experiment_id": str(locked.pk)})
    return _transition_to_recovering(locked, current)


def _transition_to_recovering(locked: FaultExperiment, current) -> FaultExperiment:
    locked.status = FaultExperiment.Status.RECOVERING
    locked.stopped_at = current
    locked.recovery_until = current + timedelta(seconds=RECOVERY_SECONDS)
    locked.save(update_fields=("status", "stopped_at", "recovery_until"))
    materialize_ground_truth(locked)
    return locked


@transaction.atomic
def _recover_missing_runtime_state(experiment: FaultExperiment, *, now) -> FaultExperiment:
    """Reconcile a database-active experiment cleared by a service restart."""

    locked = FaultExperiment.objects.select_for_update().get(pk=experiment.pk)
    if locked.status != FaultExperiment.Status.ACTIVE:
        return locked
    return _transition_to_recovering(locked, now)


def repeat_experiment(experiment: FaultExperiment, *, actor) -> FaultExperiment:
    return start_experiment(actor=actor, service=experiment.service, fault_type=experiment.fault_type, duration_seconds=experiment.duration_seconds, parameters=experiment.parameters, seed=experiment.seed, repeated_from=experiment)


def recover_expired_experiments(*, now=None) -> int:
    current = now or timezone.now()
    changed = 0
    for experiment in FaultExperiment.objects.filter(status=FaultExperiment.Status.ACTIVE):
        if experiment.expires_at and experiment.expires_at <= current:
            stop_experiment(experiment, now=current)
            changed += 1
            continue
        try:
            runtime = _send_control(experiment.service, {"action": "status"})
        except RuntimeError:
            # A temporary service outage is not proof that its fault state is
            # gone. Retry on the next watchdog tick instead of corrupting audit.
            continue
        if runtime.get("status") != "active" or runtime.get("experiment_id") != str(experiment.pk):
            _recover_missing_runtime_state(experiment, now=current)
            changed += 1
    completed = complete_expired_recoveries(now=current)
    return changed + completed
