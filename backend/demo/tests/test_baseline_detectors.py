from datetime import UTC, datetime, timedelta
import math

from django.test import TestCase

from demo.detection import MedianMadDetector, StaticThresholdDetector, persist_detection
from demo.models import DetectionDecision, TelemetryFeature


class BaselineDetectorTests(TestCase):
    window = datetime(2026, 11, 17, 10, 0, tzinfo=UTC)

    def feature(self, *, offset: int = 0, service: str = "orders-api", **values) -> TelemetryFeature:
        defaults = {
            "request_count": 100.0,
            "error_rate": 0.01,
            "latency_p95_ms": 100.0,
            "cpu_average": 25.0,
            "memory_average_mb": 128.0,
            "db_query_p95_ms": 20.0,
            "queue_depth_max": 1.0,
            "queue_oldest_age_max_seconds": 0.0,
            "queue_enqueue_count": 10.0,
            "queue_dequeue_count": 10.0,
            "failed_task_count": 0.0,
        }
        defaults.update(values)
        return TelemetryFeature.objects.create(
            schema_version="features.v2",
            window_start=self.window + timedelta(minutes=offset * 5),
            environment="local",
            service=service,
            source_window_count=5,
            feature_values={},
            **defaults,
        )

    def test_static_threshold_reports_bounded_explainable_reasons(self) -> None:
        feature = self.feature(error_rate=0.25, latency_p95_ms=600.0)

        result = StaticThresholdDetector().detect(feature)

        self.assertTrue(result.is_anomaly)
        self.assertEqual(result.severity, DetectionDecision.Severity.CRITICAL)
        self.assertIn("static.error_rate.critical", result.reasons)
        self.assertIn("static.latency_p95_ms.warning", result.reasons)

    def test_static_threshold_supports_service_override(self) -> None:
        feature = self.feature(latency_p95_ms=250.0)
        detector = StaticThresholdDetector(
            configuration_version="static.orders.v1",
            service_thresholds={
                "orders-api": {"latency_p95_ms": {"warning": 200.0, "critical": 400.0}},
            },
        )

        result = detector.detect(feature)

        self.assertTrue(result.is_anomaly)
        self.assertEqual(result.severity, DetectionDecision.Severity.WARNING)

    def test_median_mad_requires_minimum_history(self) -> None:
        feature = self.feature(offset=2, latency_p95_ms=150.0)
        history = [self.feature(offset=0), self.feature(offset=1)]

        result = MedianMadDetector(minimum_samples=3).detect(feature, history=history)

        self.assertFalse(result.is_anomaly)
        self.assertIsNone(result.score)
        self.assertEqual(result.reasons, ("median_mad.insufficient_history",))

    def test_median_mad_detects_high_outlier_with_zero_dispersion(self) -> None:
        history = [self.feature(offset=index, latency_p95_ms=100.0) for index in range(12)]
        feature = self.feature(offset=12, latency_p95_ms=400.0)

        result = MedianMadDetector().detect(feature, history=history)

        self.assertTrue(result.is_anomaly)
        self.assertEqual(result.severity, DetectionDecision.Severity.CRITICAL)
        self.assertIn("median_mad.latency_p95_ms.high", result.reasons)
        self.assertTrue(math.isfinite(result.score))
        self.assertLessEqual(result.score, 100.0)
        self.assertGreaterEqual(result.normalized_score, 0.0)
        self.assertLessEqual(result.normalized_score, 1.0)

    def test_median_mad_zero_center_is_finite_and_normalized(self) -> None:
        history = [self.feature(offset=index, db_query_p95_ms=0.0) for index in range(12)]
        feature = self.feature(offset=12, db_query_p95_ms=23.0)

        result = MedianMadDetector().detect(feature, history=history)

        self.assertTrue(result.is_anomaly)
        self.assertTrue(math.isfinite(result.score))
        self.assertAlmostEqual(result.score, 20.0)
        self.assertAlmostEqual(result.normalized_score, 20.0 / 23.5)

    def test_persistence_is_idempotent_and_traceable(self) -> None:
        feature = self.feature(error_rate=0.10)
        detector = StaticThresholdDetector(configuration_version="static.test.v1")

        first = persist_detection(feature=feature, detector=detector)
        second = persist_detection(feature=feature, detector=detector)

        self.assertEqual(first.pk, second.pk)
        self.assertEqual(DetectionDecision.objects.count(), 1)
        self.assertEqual(second.feature_id, feature.pk)
        self.assertEqual(second.detector_type, "static_threshold")
        self.assertEqual(second.detector_version, "1.1.0")
        self.assertEqual(second.configuration_version, "static.test.v1")
        self.assertEqual(second.environment, "local")
        self.assertEqual(second.service, "orders-api")
        self.assertEqual(second.score, 2.0)
        self.assertAlmostEqual(second.normalized_score, 2 / 3)
