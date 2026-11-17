import tempfile
from datetime import UTC, datetime, timedelta
from pathlib import Path

from django.test import TestCase, override_settings

from demo.detection.isolation_forest import (
    MODEL_FEATURE_NAMES,
    activate_model,
    score_with_active_model,
    train_isolation_forest,
)
from demo.models import DetectionDecision, DetectorModel, TelemetryFeature
from demo.telemetry_ingestion import FEATURE_V2_NAMES


class IsolationForestLifecycleTests(TestCase):
    start = datetime(2026, 11, 1, tzinfo=UTC)

    def feature(self, index: int, *, latency: float, error_rate: float = 0.01) -> TelemetryFeature:
        context = {name: None for name in FEATURE_V2_NAMES}
        context["time.hour_sin"] = 0.0
        context["time.hour_cos"] = 1.0
        context["rolling_15m.latency_p95_ms.mean"] = latency
        return TelemetryFeature.objects.create(
            schema_version="features.v2",
            window_start=self.start + timedelta(minutes=index * 5),
            environment="local",
            service="orders-api",
            source_window_count=5,
            request_count=100.0 + (index % 5),
            error_rate=error_rate,
            latency_p95_ms=latency,
            cpu_average=20.0 + (index % 4),
            memory_average_mb=128.0,
            db_query_p95_ms=20.0,
            queue_depth_max=1.0,
            queue_oldest_age_max_seconds=0.0,
            queue_enqueue_count=10.0,
            queue_dequeue_count=10.0,
            failed_task_count=0.0,
            feature_values=context,
        )

    def test_training_requires_minimum_time_ordered_samples(self) -> None:
        for index in range(4):
            self.feature(index, latency=100.0 + index)

        with tempfile.TemporaryDirectory() as directory, override_settings(MODEL_ARTIFACT_DIR=directory):
            with self.assertRaisesMessage(ValueError, "model_training_insufficient_samples"):
                train_isolation_forest(
                    environment="local",
                    service="orders-api",
                    start=self.start,
                    end=self.start + timedelta(hours=1),
                    minimum_samples=5,
                )

    def test_training_activation_artifact_and_scoring_are_traceable(self) -> None:
        for index in range(60):
            self.feature(index, latency=100.0 + (index % 7))

        with tempfile.TemporaryDirectory() as directory, override_settings(MODEL_ARTIFACT_DIR=directory):
            model = train_isolation_forest(
                environment="local",
                service="orders-api",
                start=self.start,
                end=self.start + timedelta(hours=5),
                minimum_samples=50,
                contamination=0.05,
                random_state=7,
            )

            self.assertEqual(model.status, DetectorModel.Status.TRAINED)
            self.assertEqual(model.sample_count, 60)
            self.assertEqual(model.feature_names, list(MODEL_FEATURE_NAMES))
            self.assertTrue((Path(directory) / model.artifact_path).is_file())

            active = activate_model(model)
            self.assertEqual(active.status, DetectorModel.Status.ACTIVE)
            self.assertIsNotNone(active.activated_at)

            outlier = self.feature(60, latency=5000.0, error_rate=0.8)
            first = score_with_active_model(outlier)
            second = score_with_active_model(outlier)

            self.assertIsNotNone(first)
            self.assertEqual(first.pk, second.pk)
            self.assertTrue(first.is_anomaly)
            self.assertEqual(first.detector_type, "isolation_forest")
            self.assertEqual(first.model_version, model.model_version)
            self.assertEqual(first.feature_id, outlier.pk)
            self.assertEqual(DetectionDecision.objects.filter(model_version=model.model_version).count(), 1)

    def test_non_local_training_is_rejected_before_artifact_creation(self) -> None:
        with tempfile.TemporaryDirectory() as directory, override_settings(MODEL_ARTIFACT_DIR=directory):
            with self.assertRaisesMessage(ValueError, "model_training_environment_must_be_local"):
                train_isolation_forest(
                    environment="production",
                    service="orders-api",
                    start=self.start,
                    end=self.start + timedelta(hours=1),
                )
            self.assertEqual(list(Path(directory).iterdir()), [])
