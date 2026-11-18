"""Validated local telemetry storage and deterministic minute aggregation."""

from __future__ import annotations

import hashlib
import json
import math
from collections import defaultdict
from datetime import UTC, datetime, timedelta
from statistics import fmean, pstdev

from django.db.models import Count
from django.db import connection, transaction
from django.utils import timezone

from .models import TelemetryAggregate, TelemetryEvent, TelemetryFeature


FEATURE_SCHEMA_V1 = "features.v1"
FEATURE_SCHEMA_V2 = "features.v2"
FEATURE_SCHEMA_VERSION = FEATURE_SCHEMA_V1
FEATURE_WINDOW_MINUTES = 5
FEATURE_V2_LAG_WINDOWS = (1, 2, 3)
FEATURE_V2_ROLLING_WINDOWS = (3, 6, 12)
SERVICE_DEPENDENCIES = (
    ("orders-api", "payments-api"),
    ("payments-api", "inventory-api"),
    ("inventory-api", "notifications-api"),
    ("notifications-api", "reporting-worker"),
)
BASE_FEATURE_FIELDS = (
    "request_count",
    "error_rate",
    "latency_p95_ms",
    "cpu_average",
    "memory_average_mb",
    "db_query_p95_ms",
    "queue_depth_max",
    "queue_oldest_age_max_seconds",
    "queue_enqueue_count",
    "queue_dequeue_count",
    "failed_task_count",
)
DEPENDENCY_SUMMARY_FIELDS = (
    "request_count",
    "error_rate",
    "latency_p95_ms",
    "queue_depth_max",
)
FEATURE_METRICS = {
    "http.server.request_count",
    "http.server.error_rate",
    "http.server.duration",
    "runtime.cpu.usage",
    "runtime.memory.usage",
    "db.query.duration",
    "queue.depth",
    "queue.oldest_message_age",
    "queue.enqueue_rate",
    "queue.dequeue_rate",
    "queue.failed_task_count",
}


def dimension_fingerprint(dimensions: dict[str, str]) -> str:
    canonical = json.dumps(dimensions, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def persist_metric_events(events: list[dict]) -> tuple[int, int]:
    """Insert normalized events atomically; existing event IDs are harmless re-delivery."""

    normalized = [
        TelemetryEvent(
            event_id=event["event_id"],
            schema_version="telemetry.v1",
            observed_at=event["observed_at"],
            environment=event["context"]["environment"],
            service=event["context"]["service"],
            instance=event["context"]["instance"],
            deployment_id=event["context"].get("deployment_id", ""),
            trace_id=event["context"].get("trace_id", ""),
            metric_name=event["metric"]["name"],
            metric_value=event["metric"]["value"],
            unit=event["metric"].get("unit", ""),
            dimensions=event.get("dimensions", {}),
            dimensions_fingerprint=dimension_fingerprint(event.get("dimensions", {})),
        )
        for event in events
    ]
    event_ids = [event.event_id for event in normalized]

    with transaction.atomic():
        existing = TelemetryEvent.objects.filter(event_id__in=event_ids).count()
        TelemetryEvent.objects.bulk_create(normalized, ignore_conflicts=True)

    return len(normalized) - existing, existing


def percentile(values: list[float], rank: float) -> float:
    """Linear interpolation percentile with a deterministic small-batch definition."""

    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    position = (len(ordered) - 1) * rank
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[lower]
    return ordered[lower] + ((ordered[upper] - ordered[lower]) * (position - lower))


def aggregate_minute(window_start: datetime, *, wait_for_lock: bool = True) -> int:
    """Upsert aggregate rows for one UTC minute; safe to re-run for the same window."""

    if timezone.is_naive(window_start):
        raise ValueError("window_start_must_be_utc_aware")
    start = window_start.astimezone(UTC).replace(second=0, microsecond=0)
    end = start + timedelta(minutes=1)
    # Telemetry arrives from several services concurrently. Serialise updates
    # for the same minute so update_or_create cannot race on the unique scope.
    lock_key = int.from_bytes(
        hashlib.sha256(start.isoformat().encode("utf-8")).digest()[:8],
        byteorder="big",
        signed=True,
    )
    with transaction.atomic():
        if connection.vendor == "postgresql":
            with connection.cursor() as cursor:
                lock_function = "pg_advisory_xact_lock" if wait_for_lock else "pg_try_advisory_xact_lock"
                cursor.execute(f"SELECT {lock_function}(%s)", [lock_key])
                if not wait_for_lock and not cursor.fetchone()[0]:
                    return 0
        return _aggregate_minute_locked(start, end)


def _aggregate_minute_locked(start: datetime, end: datetime) -> int:
    """Recompute one minute while the caller holds its advisory lock."""

    groups: dict[tuple, list[TelemetryEvent]] = defaultdict(list)

    for event in TelemetryEvent.objects.filter(observed_at__gte=start, observed_at__lt=end).order_by(
        "observed_at", "event_id"
    ):
        groups[
            (
                event.environment,
                event.service,
                event.instance,
                event.deployment_id,
                event.metric_name,
                event.unit,
                event.dimensions_fingerprint,
            )
        ].append(event)

    for scope, events in groups.items():
        values = [event.metric_value for event in events]
        defaults = {
            "event_count": len(values),
            "minimum": min(values),
            "maximum": max(values),
            "average": fmean(values),
            "last_value": values[-1],
            "p50": percentile(values, 0.50),
            "p95": percentile(values, 0.95),
            "p99": percentile(values, 0.99),
        }
        TelemetryAggregate.objects.update_or_create(
            window_start=start,
            environment=scope[0],
            service=scope[1],
            instance=scope[2],
            deployment_id=scope[3],
            metric_name=scope[4],
            unit=scope[5],
            dimensions_fingerprint=scope[6],
            defaults=defaults,
        )
    return len(groups)


def completed_minute_start(now: datetime | None = None) -> datetime:
    current = now or timezone.now()
    return (current - timedelta(minutes=2)).replace(second=0, microsecond=0)


def purge_expired_events(now: datetime | None = None) -> int:
    cutoff = (now or timezone.now()) - timedelta(days=30)
    deleted, _ = TelemetryEvent.objects.filter(ingested_at__lt=cutoff).delete()
    return deleted


def feature_window_start(value: datetime) -> datetime:
    """Return the UTC five-minute feature window containing ``value``."""

    if timezone.is_naive(value):
        raise ValueError("feature_window_must_be_utc_aware")
    normalized = value.astimezone(UTC).replace(second=0, microsecond=0)
    return normalized - timedelta(minutes=normalized.minute % FEATURE_WINDOW_MINUTES)


def _weighted_average(rows: list[TelemetryAggregate]) -> float | None:
    if not rows:
        return None
    total_count = sum(row.event_count for row in rows)
    if not total_count:
        return None
    return sum(row.average * row.event_count for row in rows) / total_count


def _maximum(rows: list[TelemetryAggregate], field: str) -> float | None:
    return max((getattr(row, field) for row in rows), default=None)


def _event_total(rows: list[TelemetryAggregate]) -> float | None:
    return float(sum(row.event_count for row in rows)) if rows else None


def _base_feature_defaults(metrics: dict[str, list[TelemetryAggregate]], source_window_count: int) -> dict:
    return {
        "source_window_count": source_window_count,
        "request_count": _event_total(metrics["http.server.request_count"]),
        "error_rate": _weighted_average(metrics["http.server.error_rate"]),
        "latency_p95_ms": _maximum(metrics["http.server.duration"], "p95"),
        "cpu_average": _weighted_average(metrics["runtime.cpu.usage"]),
        "memory_average_mb": _weighted_average(metrics["runtime.memory.usage"]),
        "db_query_p95_ms": _maximum(metrics["db.query.duration"], "p95"),
        "queue_depth_max": _maximum(metrics["queue.depth"], "last_value"),
        "queue_oldest_age_max_seconds": _maximum(metrics["queue.oldest_message_age"], "last_value"),
        "queue_enqueue_count": _event_total(metrics["queue.enqueue_rate"]),
        "queue_dequeue_count": _event_total(metrics["queue.dequeue_rate"]),
        "failed_task_count": _event_total(metrics["queue.failed_task_count"]),
    }


def feature_v2_names() -> tuple[str, ...]:
    """Return the immutable, cardinality-safe ``features.v2`` key contract."""

    names = [
        "time.hour_sin",
        "time.hour_cos",
        "time.weekday_sin",
        "time.weekday_cos",
    ]
    for lag_windows in FEATURE_V2_LAG_WINDOWS:
        lag_minutes = lag_windows * FEATURE_WINDOW_MINUTES
        names.extend(f"lag_{lag_minutes}m.{field}" for field in BASE_FEATURE_FIELDS)
    for rolling_windows in FEATURE_V2_ROLLING_WINDOWS:
        rolling_minutes = rolling_windows * FEATURE_WINDOW_MINUTES
        for field in BASE_FEATURE_FIELDS:
            names.extend(
                (
                    f"rolling_{rolling_minutes}m.{field}.mean",
                    f"rolling_{rolling_minutes}m.{field}.std",
                    f"rolling_{rolling_minutes}m.{field}.min",
                    f"rolling_{rolling_minutes}m.{field}.max",
                )
            )
    for direction in ("upstream", "downstream"):
        names.append(f"dependency.{direction}.service_count")
        for field in DEPENDENCY_SUMMARY_FIELDS:
            names.extend(
                (
                    f"dependency.{direction}.{field}.mean",
                    f"dependency.{direction}.{field}.max",
                )
            )
    names.extend(
        (
            "dependency.upstream.latency_delta_ms",
            "dependency.downstream.latency_delta_ms",
            "dependency.upstream.error_rate_delta",
            "dependency.downstream.error_rate_delta",
        )
    )
    return tuple(names)


FEATURE_V2_NAMES = feature_v2_names()


def _cyclic_time_values(window_start: datetime) -> dict[str, float]:
    hour = window_start.hour + (window_start.minute / 60)
    hour_angle = 2 * math.pi * hour / 24
    weekday_angle = 2 * math.pi * window_start.weekday() / 7
    return {
        "time.hour_sin": math.sin(hour_angle),
        "time.hour_cos": math.cos(hour_angle),
        "time.weekday_sin": math.sin(weekday_angle),
        "time.weekday_cos": math.cos(weekday_angle),
    }


def _nullable_summary(values: list[float | None]) -> tuple[float | None, float | None, float | None, float | None]:
    observed = [float(value) for value in values if value is not None]
    if not observed:
        return None, None, None, None
    return fmean(observed), pstdev(observed), min(observed), max(observed)


def _dependency_services(service: str, direction: str) -> tuple[str, ...]:
    if direction == "upstream":
        return tuple(upstream for upstream, downstream in SERVICE_DEPENDENCIES if downstream == service)
    return tuple(downstream for upstream, downstream in SERVICE_DEPENDENCIES if upstream == service)


def _dependency_values(
    current: TelemetryFeature,
    features_by_service: dict[str, TelemetryFeature],
    direction: str,
) -> dict[str, float | None]:
    services = _dependency_services(current.service, direction)
    rows = [features_by_service[service] for service in services if service in features_by_service]
    values: dict[str, float | None] = {f"dependency.{direction}.service_count": float(len(rows))}
    for field in DEPENDENCY_SUMMARY_FIELDS:
        observed = [getattr(row, field) for row in rows if getattr(row, field) is not None]
        values[f"dependency.{direction}.{field}.mean"] = fmean(observed) if observed else None
        values[f"dependency.{direction}.{field}.max"] = max(observed) if observed else None

    latency_mean = values[f"dependency.{direction}.latency_p95_ms.mean"]
    error_mean = values[f"dependency.{direction}.error_rate.mean"]
    values[f"dependency.{direction}.latency_delta_ms"] = (
        current.latency_p95_ms - latency_mean
        if current.latency_p95_ms is not None and latency_mean is not None
        else None
    )
    values[f"dependency.{direction}.error_rate_delta"] = (
        current.error_rate - error_mean
        if current.error_rate is not None and error_mean is not None
        else None
    )
    return values


def build_feature_v2_values(
    feature: TelemetryFeature,
    *,
    history: list[TelemetryFeature],
    features_by_service: dict[str, TelemetryFeature],
) -> dict[str, float | None]:
    """Build fixed temporal/dependency context from completed windows only."""

    prior_by_start = {row.window_start: row for row in history if row.window_start < feature.window_start}
    values: dict[str, float | None] = {name: None for name in FEATURE_V2_NAMES}
    values.update(_cyclic_time_values(feature.window_start))

    for lag_windows in FEATURE_V2_LAG_WINDOWS:
        lag_minutes = lag_windows * FEATURE_WINDOW_MINUTES
        prior = prior_by_start.get(feature.window_start - timedelta(minutes=lag_minutes))
        for field in BASE_FEATURE_FIELDS:
            values[f"lag_{lag_minutes}m.{field}"] = getattr(prior, field) if prior else None

    for rolling_windows in FEATURE_V2_ROLLING_WINDOWS:
        rolling_minutes = rolling_windows * FEATURE_WINDOW_MINUTES
        lower_bound = feature.window_start - timedelta(minutes=rolling_minutes)
        rows = [row for row in history if lower_bound <= row.window_start < feature.window_start]
        for field in BASE_FEATURE_FIELDS:
            mean, std, minimum, maximum = _nullable_summary([getattr(row, field) for row in rows])
            prefix = f"rolling_{rolling_minutes}m.{field}"
            values[f"{prefix}.mean"] = mean
            values[f"{prefix}.std"] = std
            values[f"{prefix}.min"] = minimum
            values[f"{prefix}.max"] = maximum

    values.update(_dependency_values(feature, features_by_service, "upstream"))
    values.update(_dependency_values(feature, features_by_service, "downstream"))
    if tuple(values) != FEATURE_V2_NAMES:
        raise ValueError("features_v2_contract_mismatch")
    return values


def materialize_feature_window(window_start: datetime) -> int:
    """Upsert v1 plus fixed-context v2 vectors for one completed five-minute window."""

    start = feature_window_start(window_start)
    end = start + timedelta(minutes=FEATURE_WINDOW_MINUTES)
    by_service: dict[tuple[str, str], dict[str, list[TelemetryAggregate]]] = defaultdict(lambda: defaultdict(list))
    aggregates = TelemetryAggregate.objects.filter(
        window_start__gte=start,
        window_start__lt=end,
        metric_name__in=FEATURE_METRICS,
    ).order_by("environment", "service", "window_start", "metric_name", "instance", "dimensions_fingerprint")
    for aggregate in aggregates:
        by_service[(aggregate.environment, aggregate.service)][aggregate.metric_name].append(aggregate)

    materialized = 0
    for (environment, service), metrics in by_service.items():
        source_windows = {row.window_start for rows in metrics.values() for row in rows}
        base_defaults = _base_feature_defaults(metrics, len(source_windows))
        TelemetryFeature.objects.update_or_create(
            schema_version=FEATURE_SCHEMA_V1,
            window_start=start,
            environment=environment,
            service=service,
            defaults={**base_defaults, "feature_values": {}},
        )
        TelemetryFeature.objects.update_or_create(
            schema_version=FEATURE_SCHEMA_V2,
            window_start=start,
            environment=environment,
            service=service,
            defaults={**base_defaults, "feature_values": {}},
        )
        materialized += 1

    v2_rows = list(
        TelemetryFeature.objects.filter(
            schema_version=FEATURE_SCHEMA_V2,
            window_start=start,
        ).order_by("environment", "service")
    )
    for feature in v2_rows:
        history = list(
            TelemetryFeature.objects.filter(
                schema_version=FEATURE_SCHEMA_V2,
                environment=feature.environment,
                service=feature.service,
                window_start__gte=feature.window_start - timedelta(minutes=60),
                window_start__lt=feature.window_start,
            ).order_by("window_start")
        )
        peers = {
            row.service: row
            for row in v2_rows
            if row.environment == feature.environment
        }
        feature.feature_values = build_feature_v2_values(
            feature,
            history=history,
            features_by_service=peers,
        )
        feature.save(update_fields=("feature_values", "materialized_at"))
    return materialized


def feature_data_quality_report(
    *,
    environment: str,
    service: str,
    start: datetime,
    end: datetime,
) -> dict:
    """Return a bounded aggregate-only quality report for ``features.v2`` rows."""

    if timezone.is_naive(start) or timezone.is_naive(end):
        raise ValueError("feature_quality_range_must_be_utc_aware")
    normalized_start = feature_window_start(start)
    normalized_end = feature_window_start(end)
    if normalized_end <= normalized_start:
        raise ValueError("feature_quality_range_must_be_positive")
    if normalized_end - normalized_start > timedelta(days=90):
        raise ValueError("feature_quality_range_too_large")
    rows = list(
        TelemetryFeature.objects.filter(
            schema_version=FEATURE_SCHEMA_V2,
            environment=environment,
            service=service,
            window_start__gte=normalized_start,
            window_start__lt=normalized_end,
        ).order_by("window_start")
    )
    duplicate_windows = list(
        TelemetryFeature.objects.filter(
            schema_version=FEATURE_SCHEMA_V2,
            environment=environment,
            service=service,
            window_start__gte=normalized_start,
            window_start__lt=normalized_end,
        )
        .values("window_start")
        .annotate(row_count=Count("id"))
        .filter(row_count__gt=1)
    )
    expected_starts = []
    cursor = normalized_start
    while cursor < normalized_end:
        expected_starts.append(cursor)
        cursor += timedelta(minutes=FEATURE_WINDOW_MINUTES)
    observed_starts = {row.window_start for row in rows}
    missing_windows = [window for window in expected_starts if window not in observed_starts]
    missing_values = {
        name: sum(row.feature_values.get(name) is None for row in rows)
        for name in FEATURE_V2_NAMES
    }
    return {
        "schema_version": FEATURE_SCHEMA_V2,
        "environment": environment,
        "service": service,
        "start": normalized_start.isoformat(),
        "end": normalized_end.isoformat(),
        "sample_count": len(rows),
        "expected_window_count": len(expected_starts),
        "duplicate_window_count": len(duplicate_windows),
        "sequence_gap_count": len(missing_windows),
        "sequence_gaps": [window.isoformat() for window in missing_windows[:100]],
        "sequence_gaps_truncated": len(missing_windows) > 100,
        "missing_value_count": missing_values,
    }


def backfill_feature_windows(start: datetime, end: datetime) -> int:
    """Materialize every five-minute window in a bounded UTC range, safely on retry."""

    if timezone.is_naive(start) or timezone.is_naive(end):
        raise ValueError("feature_backfill_range_must_be_utc_aware")
    window = feature_window_start(start)
    upper_bound = feature_window_start(end)
    materialized = 0
    while window <= upper_bound:
        materialized += materialize_feature_window(window)
        window += timedelta(minutes=FEATURE_WINDOW_MINUTES)
    return materialized
