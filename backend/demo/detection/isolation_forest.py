"""Versioned Isolation Forest training, activation and local artifact scoring."""

from __future__ import annotations

import os
import uuid
from datetime import datetime
from pathlib import Path

import joblib
from django.conf import settings
from django.db import transaction
from django.utils import timezone
from sklearn.ensemble import IsolationForest
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline

from demo.models import DetectionDecision, DetectorModel, TelemetryFeature
from demo.telemetry_ingestion import BASE_FEATURE_FIELDS, FEATURE_SCHEMA_V2, FEATURE_V2_NAMES

from .base import DetectionResult, DetectorMetadata, normalize_signed_score
from .service import persist_detection
from .training_data import normal_training_features


ISOLATION_FOREST_VERSION = "1.0.0"
MODEL_FEATURE_NAMES = (*BASE_FEATURE_FIELDS, *FEATURE_V2_NAMES)


def feature_vector(feature: TelemetryFeature, names: tuple[str, ...] = MODEL_FEATURE_NAMES) -> list[float | None]:
    values: list[float | None] = []
    for name in names:
        if name in BASE_FEATURE_FIELDS:
            values.append(getattr(feature, name))
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
    pipeline.fit([feature_vector(row) for row in rows])

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
        prediction = int(pipeline.predict(vector)[0])
        score = -float(pipeline.decision_function(vector)[0])
        is_anomaly = prediction == -1
        severity = DetectionDecision.Severity.NORMAL
        if is_anomaly:
            severity = DetectionDecision.Severity.CRITICAL if score >= 0.15 else DetectionDecision.Severity.WARNING
        return DetectionResult(
            score=score,
            normalized_score=normalize_signed_score(score),
            threshold=0.0,
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
