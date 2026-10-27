"""Validated local telemetry storage and deterministic minute aggregation."""

from __future__ import annotations

import hashlib
import json
import math
from collections import defaultdict
from datetime import UTC, datetime, timedelta
from statistics import fmean

from django.db import transaction
from django.utils import timezone

from .models import TelemetryAggregate, TelemetryEvent, TelemetryFeature


FEATURE_SCHEMA_VERSION = "features.v1"
FEATURE_WINDOW_MINUTES = 5
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


def aggregate_minute(window_start: datetime) -> int:
    """Upsert aggregate rows for one UTC minute; safe to re-run for the same window."""

    if timezone.is_naive(window_start):
        raise ValueError("window_start_must_be_utc_aware")
    start = window_start.astimezone(UTC).replace(second=0, microsecond=0)
    end = start + timedelta(minutes=1)
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


def materialize_feature_window(window_start: datetime) -> int:
    """Upsert fixed, aggregate-only vectors for one deterministic five-minute window."""

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
        TelemetryFeature.objects.update_or_create(
            schema_version=FEATURE_SCHEMA_VERSION,
            window_start=start,
            environment=environment,
            service=service,
            defaults={
                "source_window_count": len(source_windows),
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
            },
        )
        materialized += 1
    return materialized


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
