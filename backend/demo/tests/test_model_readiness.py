from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from demo.detection.readiness import model_data_readiness
from demo.models import DetectionDecision, FaultExperiment, GroundTruthWindow, SequenceJournal, TelemetryFeature


class ModelReadinessTests(TestCase):
    def setUp(self) -> None:
        self.start = timezone.now().replace(second=0, microsecond=0) - timedelta(hours=8)

    def feature(self, index: int) -> TelemetryFeature:
        return TelemetryFeature.objects.create(
            schema_version="features.v2",
            window_start=self.start + timedelta(minutes=index * 5),
            environment="local",
            service="orders-api",
            source_window_count=5,
            request_count=10,
            latency_p95_ms=100,
            feature_values={},
        )

    def report(self):
        return model_data_readiness(
            environment="local",
            service="orders-api",
            start=self.start,
            end=self.start + timedelta(hours=12),
        )

    def test_empty_scope_is_collecting_without_invented_values(self) -> None:
        report = self.report()

        self.assertEqual(report["status"], "collecting")
        self.assertEqual(report["feature_sample_count"], 0)
        self.assertIsNone(report["missing_value_ratio"])
        self.assertFalse(report["isolation_forest_ready"])
        self.assertFalse(report["lstm_ready"])

    def test_contiguous_real_windows_drive_both_readiness_gates(self) -> None:
        features = [self.feature(index) for index in range(71)]
        for index in range(60):
            SequenceJournal.objects.create(
                environment="local",
                service="orders-api",
                window_end=features[index + 11].window_start,
                sequence_length=12,
                feature_ids=[item.pk for item in features[index:index + 12]],
                split="train" if index < 42 else "validation" if index < 51 else "test",
            )

        report = self.report()

        self.assertEqual(report["status"], "lstm_ready")
        self.assertEqual(report["feature_sample_count"], 71)
        self.assertEqual(report["longest_contiguous_window_count"], 71)
        self.assertEqual(report["sequence_gap_count"], 0)
        self.assertEqual(report["candidate_sequence_count"], 60)
        self.assertEqual(report["sequence_split_counts"], {"train": 42, "validation": 9, "test": 9})
        self.assertTrue(report["isolation_forest_ready"])
        self.assertTrue(report["lstm_ready"])
        self.assertEqual(report["estimated_minutes_remaining_for_lstm"], 0)

    def test_gap_breaks_sequences_but_baseline_predictions_do_not_define_training_truth(self) -> None:
        features = [self.feature(index) for index in range(50) if index != 25]
        DetectionDecision.objects.create(
            feature=features[0], environment="local", service="orders-api",
            detector_type="static_threshold", detector_version="1.1.0",
            configuration_version="static.default.v2", score=2, normalized_score=2 / 3,
            threshold=1, is_anomaly=True, severity="critical", reasons=[],
        )

        report = self.report()

        self.assertEqual(report["feature_sample_count"], 49)
        self.assertEqual(report["eligible_isolation_forest_sample_count"], 49)
        self.assertEqual(report["sequence_gap_count"], 1)
        self.assertEqual(report["longest_contiguous_window_count"], 25)
        self.assertFalse(report["isolation_forest_ready"])
        self.assertFalse(report["lstm_ready"])

    def test_controlled_fault_and_recovery_windows_are_not_training_eligible(self) -> None:
        features = [self.feature(index) for index in range(50)]
        user = get_user_model().objects.create_superuser(username="operator", password="test-password")
        experiment = FaultExperiment.objects.create(
            environment="local",
            service="orders-api",
            fault_type=FaultExperiment.FaultType.HIGH_LATENCY,
            status=FaultExperiment.Status.COMPLETED,
            parameters={"delay_ms": 500},
            duration_seconds=60,
            seed=42,
            created_by=user,
        )
        GroundTruthWindow.objects.create(
            experiment=experiment,
            environment="local",
            service="orders-api",
            window_start=features[0].window_start,
            label=GroundTruthWindow.Label.FAULT_ACTIVE,
            fault_severity=1.0,
        )
        GroundTruthWindow.objects.create(
            experiment=experiment,
            environment="local",
            service="orders-api",
            window_start=features[1].window_start,
            label=GroundTruthWindow.Label.RECOVERING,
            fault_severity=0.5,
        )

        report = self.report()

        self.assertEqual(report["feature_sample_count"], 50)
        self.assertEqual(report["eligible_isolation_forest_sample_count"], 48)
        self.assertFalse(report["isolation_forest_ready"])
