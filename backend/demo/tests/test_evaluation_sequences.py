from datetime import UTC, datetime, timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase

from demo.detection.base import DetectorMetadata
from demo.detection.evaluation import evaluate_detector
from demo.detection.sequences import materialize_sequence_journals, train_lstm_prototype
from demo.models import DetectionDecision, FaultExperiment, GroundTruthWindow, SequenceJournal, TelemetryFeature
from demo.telemetry_ingestion import FEATURE_V2_NAMES


class EvaluationAndSequenceTests(TestCase):
    start = datetime(2026, 11, 10, tzinfo=UTC)

    def setUp(self) -> None:
        self.admin = get_user_model().objects.create_user(username="evaluation-admin", password="unused", is_superuser=True)

    def feature(self, index: int, *, anomaly_signal: float = 0.0) -> TelemetryFeature:
        context = {name: 0.0 for name in FEATURE_V2_NAMES}
        context["rolling_15m.latency_p95_ms.mean"] = 100.0 + anomaly_signal
        return TelemetryFeature.objects.create(
            schema_version="features.v2", window_start=self.start + timedelta(minutes=index * 5),
            environment="local", service="orders-api", source_window_count=5,
            request_count=100.0, error_rate=anomaly_signal / 10000, latency_p95_ms=100.0 + anomaly_signal,
            cpu_average=20.0, memory_average_mb=128.0, db_query_p95_ms=20.0,
            queue_depth_max=1.0, queue_oldest_age_max_seconds=0.0,
            queue_enqueue_count=10.0, queue_dequeue_count=10.0, failed_task_count=0.0,
            feature_values=context,
        )

    def experiment(self) -> FaultExperiment:
        return FaultExperiment.objects.create(
            environment="local", service="orders-api", fault_type=FaultExperiment.FaultType.HIGH_LATENCY,
            status=FaultExperiment.Status.COMPLETED, parameters={"delay_ms": 1000.0}, duration_seconds=60,
            seed=42, created_by=self.admin, started_at=self.start + timedelta(minutes=10),
            expires_at=self.start + timedelta(minutes=25), stopped_at=self.start + timedelta(minutes=25),
            recovery_until=self.start + timedelta(minutes=35),
        )

    def test_evaluation_calculates_confusion_and_delay_metrics_idempotently(self) -> None:
        experiment = self.experiment()
        labels = ("normal", "normal", "fault_active", "fault_active", "fault_active", "recovering", "recovering")
        predictions = (False, True, False, True, True, True, False)
        metadata = DetectorMetadata("static_threshold", "1.0.0", "static.test.v1")
        for index, (label, prediction) in enumerate(zip(labels, predictions)):
            feature = self.feature(index)
            GroundTruthWindow.objects.create(experiment=experiment, environment="local", service="orders-api", window_start=feature.window_start, label=label, fault_severity=0.2)
            DetectionDecision.objects.create(
                feature=feature, environment="local", service="orders-api", detector_type=metadata.detector_type,
                detector_version=metadata.detector_version, configuration_version=metadata.configuration_version,
                is_anomaly=prediction, severity="warning" if prediction else "normal", reasons=[],
            )

        first = evaluate_detector(experiment, metadata)
        second = evaluate_detector(experiment, metadata)

        self.assertEqual(first.pk, second.pk)
        self.assertEqual((second.true_positive, second.false_positive, second.true_negative, second.false_negative), (2, 1, 1, 1))
        self.assertAlmostEqual(second.precision, 2 / 3)
        self.assertAlmostEqual(second.recall, 2 / 3)
        self.assertAlmostEqual(second.f1_score, 2 / 3)
        self.assertEqual(second.false_positive_rate, 0.5)
        self.assertEqual(second.detection_delay_seconds, 300.0)
        self.assertEqual(second.recovery_delay_seconds, 300.0)

    def test_sequence_journals_are_contiguous_time_ordered_and_lstm_gated(self) -> None:
        experiment = self.experiment()
        for index in range(80):
            feature = self.feature(index, anomaly_signal=2000.0 if index >= 60 else float(index % 5))
            if index >= 60:
                GroundTruthWindow.objects.create(experiment=experiment, environment="local", service="orders-api", window_start=feature.window_start, label=GroundTruthWindow.Label.FAULT_ACTIVE, fault_severity=0.8)

        count = materialize_sequence_journals(environment="local", service="orders-api", sequence_length=12)
        journals = list(SequenceJournal.objects.order_by("window_end"))

        self.assertEqual(count, 69)
        self.assertEqual(len(journals), 69)
        self.assertEqual(SequenceJournal.objects.filter(split="train").count(), 48)
        self.assertEqual(SequenceJournal.objects.filter(split="validation").count(), 10)
        self.assertEqual(SequenceJournal.objects.filter(split="test").count(), 11)
        self.assertLess(SequenceJournal.objects.filter(split="train").latest("window_end").window_end, SequenceJournal.objects.filter(split="validation").earliest("window_end").window_end)
        for journal in journals:
            source_windows = list(TelemetryFeature.objects.filter(pk__in=journal.feature_ids).order_by("window_start").values_list("window_start", flat=True))
            self.assertEqual(len(source_windows), 12)
            self.assertEqual(source_windows[-1], journal.window_end)
            self.assertTrue(all(right - left == timedelta(minutes=5) for left, right in zip(source_windows, source_windows[1:])))

        result = train_lstm_prototype(environment="local", service="orders-api", minimum_sequences=60, epochs=5, seed=7)
        self.assertEqual((result.train_samples, result.validation_samples, result.test_samples), (48, 10, 11))
        self.assertGreaterEqual(result.validation_accuracy, 0.0)
        self.assertLessEqual(result.validation_accuracy, 1.0)
        self.assertGreaterEqual(result.test_accuracy, 0.0)
        self.assertLessEqual(result.test_accuracy, 1.0)

    def test_lstm_prototype_rejects_insufficient_sequences(self) -> None:
        with self.assertRaisesMessage(ValueError, "lstm_minimum_sequences_not_met"):
            train_lstm_prototype(environment="local", service="orders-api", minimum_sequences=60)
