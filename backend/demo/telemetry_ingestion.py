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

from .models import TelemetryAggregate, TelemetryEvent


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
