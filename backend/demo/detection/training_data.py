"""Ground-truth-aware feature selection for model training and readiness."""

from __future__ import annotations

from datetime import datetime

from django.db.models import QuerySet, Subquery

from demo.models import GroundTruthWindow, TelemetryFeature
from demo.telemetry_ingestion import FEATURE_SCHEMA_V2


def normal_training_features(
    *,
    environment: str,
    service: str,
    start: datetime,
    end: datetime,
) -> QuerySet[TelemetryFeature]:
    """Return completed feature rows not covered by known fault/recovery truth.

    Baseline detector decisions intentionally do not filter this queryset. They
    are predictions to compare, not labels that may define another model's
    training population.
    """

    non_normal_windows = GroundTruthWindow.objects.filter(
        environment=environment,
        service=service,
        window_start__gte=start,
        window_start__lt=end,
        label__in=(
            GroundTruthWindow.Label.FAULT_ACTIVE,
            GroundTruthWindow.Label.RECOVERING,
        ),
    ).values("window_start")
    return (
        TelemetryFeature.objects.filter(
            schema_version=FEATURE_SCHEMA_V2,
            environment=environment,
            service=service,
            window_start__gte=start,
            window_start__lt=end,
        )
        .exclude(window_start__in=Subquery(non_normal_windows))
        .order_by("window_start", "id")
    )
