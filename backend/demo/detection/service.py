"""Retry-safe persistence for traceable detector decisions."""

from __future__ import annotations

from demo.models import DetectionDecision, TelemetryFeature

from .base import Detector


def persist_detection(
    *,
    feature: TelemetryFeature,
    detector: Detector,
    history: list[TelemetryFeature] | None = None,
) -> DetectionDecision:
    metadata = detector.metadata()
    result = detector.detect(feature, history=history)
    decision, _ = DetectionDecision.objects.update_or_create(
        feature=feature,
        detector_type=metadata.detector_type,
        detector_version=metadata.detector_version,
        configuration_version=metadata.configuration_version,
        model_version=metadata.model_version,
        defaults={
            "environment": feature.environment,
            "service": feature.service,
            "score": result.score,
            "normalized_score": result.normalized_score,
            "threshold": result.threshold,
            "is_anomaly": result.is_anomaly,
            "severity": result.severity,
            "reasons": list(result.reasons),
        },
    )
    return decision


def score_feature_window(window_start) -> int:
    """Run retry-safe baseline and active-model scoring for one completed window."""

    from datetime import timedelta

    from demo.telemetry_ingestion import FEATURE_SCHEMA_V2

    from .baseline import MedianMadDetector, StaticThresholdDetector
    from .isolation_forest import score_with_active_model

    decisions = 0
    features = TelemetryFeature.objects.filter(
        schema_version=FEATURE_SCHEMA_V2,
        window_start=window_start,
    ).order_by("environment", "service")
    for feature in features:
        history = list(
            TelemetryFeature.objects.filter(
                schema_version=FEATURE_SCHEMA_V2,
                environment=feature.environment,
                service=feature.service,
                window_start__gte=feature.window_start - timedelta(hours=24),
                window_start__lt=feature.window_start,
            ).order_by("window_start")
        )
        persist_detection(feature=feature, detector=StaticThresholdDetector())
        persist_detection(feature=feature, detector=MedianMadDetector(), history=history)
        decisions += 2
        if score_with_active_model(feature) is not None:
            decisions += 1
    return decisions
