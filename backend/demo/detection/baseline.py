"""Explainable baseline detectors used to evaluate later ML models."""

from __future__ import annotations

import math
from statistics import median

from demo.models import DetectionDecision, TelemetryFeature

from .base import DetectionResult, DetectorMetadata, normalize_positive_score


DEFAULT_STATIC_THRESHOLDS = {
    "error_rate": {"warning": 0.05, "critical": 0.20},
    "latency_p95_ms": {"warning": 500.0, "critical": 1000.0},
    "cpu_average": {"warning": 80.0, "critical": 95.0},
    "queue_depth_max": {"warning": 50.0, "critical": 200.0},
    "failed_task_count": {"warning": 1.0, "critical": 5.0},
}
DEFAULT_MAD_FIELDS = (
    "error_rate",
    "latency_p95_ms",
    "cpu_average",
    "memory_average_mb",
    "db_query_p95_ms",
    "queue_depth_max",
    "queue_oldest_age_max_seconds",
    "failed_task_count",
)


def _severity_rank(severity: str) -> int:
    return {
        DetectionDecision.Severity.NORMAL: 0,
        DetectionDecision.Severity.WARNING: 1,
        DetectionDecision.Severity.CRITICAL: 2,
    }[severity]


class StaticThresholdDetector:
    """Service-aware fixed limits providing an explainable first baseline."""

    def __init__(
        self,
        *,
        configuration_version: str = "static.default.v2",
        thresholds: dict[str, dict[str, float]] | None = None,
        service_thresholds: dict[str, dict[str, dict[str, float]]] | None = None,
    ) -> None:
        self.thresholds = thresholds or DEFAULT_STATIC_THRESHOLDS
        self.service_thresholds = service_thresholds or {}
        self.configuration_version = configuration_version

    def metadata(self) -> DetectorMetadata:
        return DetectorMetadata("static_threshold", "1.1.0", self.configuration_version)

    def detect(
        self,
        feature: TelemetryFeature,
        *,
        history: list[TelemetryFeature] | None = None,
    ) -> DetectionResult:
        del history
        score = 0.0
        severity = DetectionDecision.Severity.NORMAL
        reasons: list[str] = []
        thresholds = self.service_thresholds.get(feature.service, self.thresholds)
        for field, limits in thresholds.items():
            value = getattr(feature, field)
            if value is None:
                continue
            warning = limits["warning"]
            critical = limits["critical"]
            score = max(score, value / warning if warning else 0.0)
            field_severity = DetectionDecision.Severity.NORMAL
            if value >= critical:
                field_severity = DetectionDecision.Severity.CRITICAL
                reasons.append(f"static.{field}.critical")
            elif value >= warning:
                field_severity = DetectionDecision.Severity.WARNING
                reasons.append(f"static.{field}.warning")
            if _severity_rank(field_severity) > _severity_rank(severity):
                severity = field_severity
        return DetectionResult(
            score=score,
            normalized_score=normalize_positive_score(score, 1.0),
            threshold=1.0,
            is_anomaly=severity != DetectionDecision.Severity.NORMAL,
            severity=severity,
            reasons=tuple(reasons[:16]),
        )


class MedianMadDetector:
    """Robust rolling detector based on median absolute deviation (MAD)."""

    def __init__(
        self,
        *,
        configuration_version: str = "median-mad.default.v2",
        fields: tuple[str, ...] = DEFAULT_MAD_FIELDS,
        minimum_samples: int = 12,
        warning_score: float = 3.5,
        critical_score: float = 7.0,
    ) -> None:
        self.configuration_version = configuration_version
        self.fields = fields
        self.minimum_samples = minimum_samples
        self.warning_score = warning_score
        self.critical_score = critical_score

    def metadata(self) -> DetectorMetadata:
        return DetectorMetadata("median_mad", "1.1.0", self.configuration_version)

    @staticmethod
    def _robust_z(value: float, samples: list[float]) -> float:
        if not math.isfinite(value) or any(not math.isfinite(sample) for sample in samples):
            return 0.0
        center = median(samples)
        mad = median(abs(sample - center) for sample in samples)
        if mad == 0:
            scale = max(abs(center) * 0.05, abs(value) * 0.05, 1e-6)
            return max(-100.0, min(100.0, (value - center) / scale))
        return max(-100.0, min(100.0, 0.6744897501960817 * (value - center) / mad))

    def detect(
        self,
        feature: TelemetryFeature,
        *,
        history: list[TelemetryFeature] | None = None,
    ) -> DetectionResult:
        prior = [row for row in (history or []) if row.window_start < feature.window_start]
        if len(prior) < self.minimum_samples:
            return DetectionResult(
                score=None,
                normalized_score=None,
                threshold=self.warning_score,
                is_anomaly=False,
                severity=DetectionDecision.Severity.NORMAL,
                reasons=("median_mad.insufficient_history",),
            )

        scores: list[tuple[str, float]] = []
        for field in self.fields:
            value = getattr(feature, field)
            samples = [getattr(row, field) for row in prior if getattr(row, field) is not None]
            if value is None or len(samples) < self.minimum_samples:
                continue
            scores.append((field, self._robust_z(float(value), [float(sample) for sample in samples])))
        if not scores:
            return DetectionResult(
                score=None,
                normalized_score=None,
                threshold=self.warning_score,
                is_anomaly=False,
                severity=DetectionDecision.Severity.NORMAL,
                reasons=("median_mad.insufficient_observations",),
            )

        positive_scores = [(field, max(0.0, score)) for field, score in scores]
        maximum = max(score for _, score in positive_scores)
        severity = DetectionDecision.Severity.NORMAL
        if maximum >= self.critical_score:
            severity = DetectionDecision.Severity.CRITICAL
        elif maximum >= self.warning_score:
            severity = DetectionDecision.Severity.WARNING
        reasons = tuple(
            f"median_mad.{field}.high"
            for field, score in sorted(positive_scores, key=lambda item: item[1], reverse=True)
            if score >= self.warning_score
        )
        return DetectionResult(
            score=maximum,
            normalized_score=normalize_positive_score(maximum, self.warning_score),
            threshold=self.warning_score,
            is_anomaly=severity != DetectionDecision.Severity.NORMAL,
            severity=severity,
            reasons=reasons[:16],
        )
