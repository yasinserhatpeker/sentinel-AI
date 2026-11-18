"""Versioned Isolation Forest training, activation and local artifact scoring."""

from __future__ import annotations

import os
import uuid
from datetime import datetime
from pathlib import Path

import joblib
import numpy as np
from django.conf import settings
from django.db import transaction
from django.utils import timezone
from sklearn.ensemble import IsolationForest
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline

from demo.models import DetectionDecision, DetectorModel, TelemetryFeature
from demo.telemetry_ingestion import BASE_FEATURE_FIELDS, FEATURE_SCHEMA_V2

from .base import DetectionResult, DetectorMetadata, normalize_signed_score
from .service import persist_detection
from .training_data import normal_training_features


ISOLATION_FOREST_VERSION = "1.1.0"
RELATIVE_FEATURE_PREFIX = "relative_to_15m."
RELATIVE_FEATURE_NAMES = tuple(f"{RELATIVE_FEATURE_PREFIX}{name}" for name in BASE_FEATURE_FIELDS)
CONTEXT_FEATURE_NAMES = (
    "time.hour_sin",
    "time.hour_cos",
    "time.weekday_sin",
    "time.weekday_cos",
    "dependency.upstream.latency_delta_ms",
    "dependency.downstream.latency_delta_ms",
    "dependency.upstream.error_rate_delta",
    "dependency.downstream.error_rate_delta",
)
# Keep the model dimensionality proportional to the small local training set.
# Current values preserve absolute service behaviour, relative values expose
# sudden deviations, and a small context set retains time/dependency signals.
MODEL_FEATURE_NAMES = (*BASE_FEATURE_FIELDS, *RELATIVE_FEATURE_NAMES, *CONTEXT_FEATURE_NAMES)


def calculate_training_diagnostics(
    pipeline: Pipeline,
    vectors: list[list[float | None]],
    *,
    score_threshold: float = 0.0,
) -> dict[str, float | int]:
    """Return finite unsupervised diagnostics without claiming labelled accuracy."""

    raw_scores = -pipeline.decision_function(vectors)
    predicted_anomaly_count = int(np.count_nonzero(raw_scores >= score_threshold))
    sample_count = len(vectors)
    return {
        "predicted_anomaly_count": predicted_anomaly_count,
        "predicted_anomaly_rate": predicted_anomaly_count / sample_count if sample_count else 0.0,
        "score_min": float(np.min(raw_scores)),
        "score_mean": float(np.mean(raw_scores)),
        "score_p50": float(np.percentile(raw_scores, 50)),
        "score_p95": float(np.percentile(raw_scores, 95)),
        "score_max": float(np.max(raw_scores)),
    }


def feature_vector(feature: TelemetryFeature, names: tuple[str, ...] = MODEL_FEATURE_NAMES) -> list[float | None]:
    values: list[float | None] = []
    for name in names:
        if name in BASE_FEATURE_FIELDS:
            values.append(getattr(feature, name))
        elif name.startswith(RELATIVE_FEATURE_PREFIX):
            field = name.removeprefix(RELATIVE_FEATURE_PREFIX)
            current = getattr(feature, field)
            baseline = feature.feature_values.get(f"rolling_15m.{field}.mean")
            values.append(
                None
                if current is None or baseline is None
                else (current - baseline) / (abs(baseline) + 1e-6)
            )
        else:
            values.append(feature.feature_values.get(name))
    return values


def _artifact_root() -> Path:
    root = Path(settings.MODEL_ARTIFACT_DIR).resolve()
    root.mkdir(parents=True, exist_ok=True)
    return root


def train_isolation_forest(
    *,
    environment: str,
    service: str,
    start: datetime,
    end: datetime,
    minimum_samples: int = 50,
    contamination: float = 0.05,
    random_state: int = 42,
) -> DetectorModel:
    """Train from time-ordered rows outside labelled fault/recovery windows."""

    if environment != "local":
        raise ValueError("model_training_environment_must_be_local")
    if timezone.is_naive(start) or timezone.is_naive(end) or end <= start:
        raise ValueError("model_training_range_invalid")
    if not 0 < contamination <= 0.5:
        raise ValueError("model_contamination_invalid")
    rows = list(normal_training_features(
        environment=environment,
        service=service,
        start=start,
        end=end,
    ))
    if len(rows) < minimum_samples:
        raise ValueError("model_training_insufficient_samples")

    pipeline = Pipeline(
        steps=(
            ("imputer", SimpleImputer(strategy="median", keep_empty_features=True)),
            (
                "model",
                IsolationForest(
                    n_estimators=200,
                    contamination=contamination,
                    random_state=random_state,
                    n_jobs=1,
                ),
            ),
        )
    )
    vectors = [feature_vector(row) for row in rows]
    pipeline.fit(vectors)
    training_scores = -pipeline.decision_function(vectors)
    score_threshold = float(np.percentile(training_scores, (1.0 - contamination) * 100.0))
    training_diagnostics = calculate_training_diagnostics(
        pipeline,
        vectors,
        score_threshold=score_threshold,
    )

    model_version = f"if-{uuid.uuid4().hex}"
    artifact_name = f"{model_version}.joblib"
    artifact_root = _artifact_root()
    artifact_path = artifact_root / artifact_name
    temporary_path = artifact_root / f".{artifact_name}.tmp"
    payload = {
        "detector_type": "isolation_forest",
        "detector_version": ISOLATION_FOREST_VERSION,
        "model_version": model_version,
        "feature_schema_version": FEATURE_SCHEMA_V2,
        "feature_names": list(MODEL_FEATURE_NAMES),
        "score_threshold": score_threshold,
        "pipeline": pipeline,
    }
    joblib.dump(payload, temporary_path)
    os.replace(temporary_path, artifact_path)
    try:
        return DetectorModel.objects.create(
            model_version=model_version,
            detector_version=ISOLATION_FOREST_VERSION,
            feature_schema_version=FEATURE_SCHEMA_V2,
            environment=environment,
            service=service,
            status=DetectorModel.Status.TRAINED,
            configuration={
                "minimum_samples": minimum_samples,
                "contamination": contamination,
                "random_state": random_state,
                "n_estimators": 200,
                "score_threshold": score_threshold,
                "training_diagnostics": training_diagnostics,
            },
            feature_names=list(MODEL_FEATURE_NAMES),
            sample_count=len(rows),
            trained_from=rows[0].window_start,
            trained_until=rows[-1].window_start,
            artifact_path=artifact_name,
        )
    except Exception:
        artifact_path.unlink(missing_ok=True)
        raise


@transaction.atomic
def activate_model(model: DetectorModel) -> DetectorModel:
    """Activate exactly one model per local environment/service scope."""

    locked = DetectorModel.objects.select_for_update().get(pk=model.pk)
    if locked.status not in (DetectorModel.Status.TRAINED, DetectorModel.Status.ACTIVE):
        raise ValueError("model_status_not_activatable")
    DetectorModel.objects.filter(
        environment=locked.environment,
        service=locked.service,
        status=DetectorModel.Status.ACTIVE,
    ).exclude(pk=locked.pk).update(status=DetectorModel.Status.RETIRED)
    locked.status = DetectorModel.Status.ACTIVE
    locked.activated_at = timezone.now()
    locked.save(update_fields=("status", "activated_at"))
    return locked


def _load_artifact(model: DetectorModel) -> dict:
    root = _artifact_root()
    artifact_path = (root / model.artifact_path).resolve()
    if artifact_path.parent != root or artifact_path.name != model.artifact_path:
        raise ValueError("model_artifact_path_invalid")
    payload = joblib.load(artifact_path)
    if (
        payload.get("model_version") != model.model_version
        or payload.get("feature_schema_version") != FEATURE_SCHEMA_V2
        or payload.get("feature_names") != model.feature_names
    ):
        raise ValueError("model_artifact_metadata_mismatch")
    return payload


class IsolationForestDetector:
    def __init__(self, model: DetectorModel) -> None:
        self.model = model
        self.payload = _load_artifact(model)

    def metadata(self) -> DetectorMetadata:
        return DetectorMetadata(
            "isolation_forest",
            self.model.detector_version,
            f"isolation-forest.{self.model.model_version}",
            self.model.model_version,
        )

    def detect(
        self,
        feature: TelemetryFeature,
        *,
        history: list[TelemetryFeature] | None = None,
    ) -> DetectionResult:
        del history
        pipeline = self.payload["pipeline"]
        vector = [feature_vector(feature, tuple(self.model.feature_names))]
        score = -float(pipeline.decision_function(vector)[0])
        threshold = float(self.payload.get("score_threshold", 0.0))
        score_margin = score - threshold
        is_anomaly = score_margin >= 0.0
        severity = DetectionDecision.Severity.NORMAL
        if is_anomaly:
            severity = DetectionDecision.Severity.CRITICAL if score_margin >= 0.15 else DetectionDecision.Severity.WARNING
        return DetectionResult(
            score=score,
            normalized_score=normalize_signed_score(score_margin),
            threshold=threshold,
            is_anomaly=is_anomaly,
            severity=severity,
            reasons=("isolation_forest.outlier",) if is_anomaly else (),
        )


def score_with_active_model(feature: TelemetryFeature) -> DetectionDecision | None:
    model = DetectorModel.objects.filter(
        environment=feature.environment,
        service=feature.service,
        status=DetectorModel.Status.ACTIVE,
    ).order_by("-activated_at").first()
    if model is None:
        return None
    return persist_detection(feature=feature, detector=IsolationForestDetector(model))
