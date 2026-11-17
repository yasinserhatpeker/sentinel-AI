"""Shared anomaly-detector protocol and bounded decision values."""

from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Protocol

from demo.models import TelemetryFeature


@dataclass(frozen=True)
class DetectorMetadata:
    detector_type: str
    detector_version: str
    configuration_version: str
    model_version: str = ""


@dataclass(frozen=True)
class DetectionResult:
    score: float | None
    normalized_score: float | None
    threshold: float | None
    is_anomaly: bool
    severity: str
    reasons: tuple[str, ...]


def normalize_positive_score(score: float | None, threshold: float | None) -> float | None:
    """Map a non-negative detector score to [0, 1] with threshold at 0.5."""

    if score is None:
        return None
    if not math.isfinite(score):
        return 1.0 if score > 0 else 0.0
    positive = max(0.0, score)
    scale = max(abs(threshold or 0.0), 1e-9)
    return min(1.0, positive / (positive + scale))


def normalize_signed_score(score: float | None, *, scale: float = 0.05) -> float | None:
    """Map a signed decision-function score to [0, 1] with zero at 0.5."""

    if score is None:
        return None
    if not math.isfinite(score):
        return 1.0 if score > 0 else 0.0
    exponent = max(-60.0, min(60.0, -score / max(scale, 1e-9)))
    return 1.0 / (1.0 + math.exp(exponent))


class Detector(Protocol):
    def metadata(self) -> DetectorMetadata: ...

    def detect(
        self,
        feature: TelemetryFeature,
        *,
        history: list[TelemetryFeature] | None = None,
    ) -> DetectionResult: ...
