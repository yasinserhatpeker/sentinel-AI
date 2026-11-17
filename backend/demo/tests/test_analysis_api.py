from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from demo.models import DetectionDecision, DetectorEvaluation, DetectorModel, FaultExperiment, TelemetryFeature
from demo.detection.sequences import LstmPrototypeResult
from demo.tests.helpers import bearer_token, create_superuser


class AnalysisApiTests(TestCase):
    def setUp(self) -> None:
        self.client = APIClient()
        self.admin = create_superuser()
        self.ordinary = get_user_model().objects.create_user(username="ordinary-api", password="unused")
        self.now = timezone.now().replace(second=0, microsecond=0)

    def auth(self, user=None) -> dict:
        return {"HTTP_AUTHORIZATION": bearer_token(user or self.admin)}

    def scope(self) -> dict:
        return {"environment": "local", "service": "orders-api", "start": (self.now - timedelta(days=1)).isoformat(), "end": (self.now + timedelta(days=1)).isoformat()}

    def feature(self) -> TelemetryFeature:
        return TelemetryFeature.objects.create(
            schema_version="features.v2", window_start=self.now, environment="local", service="orders-api",
            source_window_count=5, request_count=100, error_rate=0.2, latency_p95_ms=800,
            feature_values={},
        )

    def model(self) -> DetectorModel:
        return DetectorModel.objects.create(
            model_version="if-api-test", detector_version="1.0.0", environment="local", service="orders-api",
            status=DetectorModel.Status.TRAINED, configuration={"contamination": 0.05}, feature_names=["latency_p95_ms"],
            sample_count=50, trained_from=self.now - timedelta(hours=5), trained_until=self.now,
            artifact_path="if-api-test.joblib",
        )

    def experiment(self) -> FaultExperiment:
        return FaultExperiment.objects.create(
            environment="local", service="orders-api", fault_type=FaultExperiment.FaultType.HIGH_LATENCY,
            status=FaultExperiment.Status.ACTIVE, parameters={"delay_ms": 500.0}, duration_seconds=60,
            seed=42, created_by=self.admin, started_at=self.now, expires_at=self.now + timedelta(seconds=60),
        )

    def test_anomaly_list_detail_require_super_admin_and_explicit_scope(self) -> None:
        feature = self.feature()
        decision = DetectionDecision.objects.create(
            feature=feature, environment="local", service="orders-api", detector_type="static_threshold",
            detector_version="1.0.0", configuration_version="static.default.v1", score=1.6,
            threshold=1.0, is_anomaly=True, severity="warning", reasons=["static.latency_p95_ms.warning"],
        )
        unauthenticated = self.client.get("/api/anomalies/v1/", self.scope())
        ordinary = self.client.get("/api/anomalies/v1/", self.scope(), **self.auth(self.ordinary))
        missing_scope = self.client.get("/api/anomalies/v1/", {"environment": "local"}, **self.auth())
        listed = self.client.get("/api/anomalies/v1/", self.scope(), **self.auth())
        detail = self.client.get(f"/api/anomalies/v1/{decision.pk}/", {"environment": "local"}, **self.auth())

        self.assertEqual(unauthenticated.status_code, 401)
        self.assertEqual(ordinary.status_code, 403)
        self.assertEqual(missing_scope.status_code, 400)
        self.assertEqual(listed.status_code, 200)
        self.assertEqual(listed.data["results"][0]["id"], str(decision.pk))
        self.assertEqual(detail.data["anomaly"]["evidence"]["feature_id"], feature.pk)
        self.assertNotIn("feature_values", detail.data["anomaly"]["evidence"])

    @patch("demo.views.train_isolation_forest")
    def test_model_train_list_and_activate_are_scoped(self, train_mock) -> None:
        model = self.model()
        train_mock.return_value = model
        payload = {**self.scope(), "minimum_samples": 50, "contamination": 0.05, "random_state": 42}
        ordinary = self.client.post("/api/models/v1/train/", payload, format="json", **self.auth(self.ordinary))
        trained = self.client.post("/api/models/v1/train/", payload, format="json", **self.auth())
        listed = self.client.get("/api/models/v1/", self.scope(), **self.auth())
        activated = self.client.post(f"/api/models/v1/{model.pk}/activate/", {"environment": "local"}, format="json", **self.auth())

        self.assertEqual(ordinary.status_code, 403)
        self.assertEqual(trained.status_code, 201)
        self.assertEqual(listed.data["results"][0]["model_version"], model.model_version)
        self.assertNotIn("artifact_path", listed.data["results"][0])
        self.assertEqual(activated.data["model"]["status"], "active")

    def test_model_readiness_requires_super_admin_and_explicit_scope(self) -> None:
        self.feature()

        unauthenticated = self.client.get("/api/models/v1/readiness/", self.scope())
        ordinary = self.client.get("/api/models/v1/readiness/", self.scope(), **self.auth(self.ordinary))
        missing_scope = self.client.get("/api/models/v1/readiness/", {"environment": "local"}, **self.auth())
        readiness = self.client.get("/api/models/v1/readiness/", self.scope(), **self.auth())

        self.assertEqual(unauthenticated.status_code, 401)
        self.assertEqual(ordinary.status_code, 403)
        self.assertEqual(missing_scope.status_code, 400)
        self.assertEqual(readiness.status_code, 200)
        self.assertEqual(readiness.data["schema_version"], "model-readiness.v1")
        self.assertEqual(readiness.data["feature_sample_count"], 1)
        self.assertFalse(readiness.data["isolation_forest_ready"])

    @patch("demo.views.train_lstm_prototype")
    @patch("demo.views.materialize_sequence_journals")
    def test_lstm_prototype_is_super_admin_scoped_and_never_activated(self, materialize_mock, train_mock) -> None:
        materialize_mock.return_value = 69
        train_mock.return_value = LstmPrototypeResult(48, 10, 11, 0.8, 0.75)
        payload = {**self.scope(), "minimum_sequences": 60, "sequence_length": 12, "epochs": 5, "seed": 7}

        ordinary = self.client.post("/api/models/v1/lstm-prototype/train/", payload, format="json", **self.auth(self.ordinary))
        trained = self.client.post("/api/models/v1/lstm-prototype/train/", payload, format="json", **self.auth())

        self.assertEqual(ordinary.status_code, 403)
        self.assertEqual(trained.status_code, 200)
        self.assertEqual(trained.data["schema_version"], "lstm-prototype-result.v1")
        self.assertEqual(trained.data["materialized_sequence_count"], 69)
        self.assertEqual((trained.data["train_samples"], trained.data["validation_samples"], trained.data["test_samples"]), (48, 10, 11))
        self.assertFalse(trained.data["activated"])

    @patch("demo.views.train_isolation_forest", side_effect=ValueError("model_training_insufficient_samples"))
    def test_model_training_returns_explicit_readiness_conflict(self, train_mock) -> None:
        response = self.client.post(
            "/api/models/v1/train/",
            {**self.scope(), "minimum_samples": 50, "contamination": 0.05, "random_state": 42},
            format="json",
            **self.auth(),
        )

        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.data, {"error": {"code": "model_training_insufficient_samples"}})

    @patch("demo.views.materialize_sequence_journals", return_value=0)
    @patch("demo.views.train_lstm_prototype", side_effect=ValueError("lstm_minimum_sequences_not_met"))
    def test_lstm_training_returns_explicit_readiness_conflict(self, train_mock, materialize_mock) -> None:
        response = self.client.post(
            "/api/models/v1/lstm-prototype/train/",
            {**self.scope(), "minimum_sequences": 60, "sequence_length": 12, "epochs": 5, "seed": 7},
            format="json",
            **self.auth(),
        )

        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.data, {"error": {"code": "lstm_minimum_sequences_not_met"}})

    @patch("demo.views.start_experiment")
    @patch("demo.views.stop_experiment")
    @patch("demo.views.repeat_experiment")
    def test_fault_mutations_and_history_require_super_admin(self, repeat_mock, stop_mock, start_mock) -> None:
        experiment = self.experiment()
        start_mock.return_value = experiment
        stop_mock.return_value = experiment
        repeat_mock.return_value = experiment
        payload = {"environment": "local", "service": "orders-api", "fault_type": "high_latency", "duration_seconds": 60, "parameters": {"delay_ms": 500}, "seed": 42}

        ordinary = self.client.post("/api/fault-experiments/v1/", payload, format="json", **self.auth(self.ordinary))
        created = self.client.post("/api/fault-experiments/v1/", payload, format="json", **self.auth())
        history = self.client.get("/api/fault-experiments/v1/", self.scope(), **self.auth())
        stopped = self.client.post(f"/api/fault-experiments/v1/{experiment.pk}/stop/", {"environment": "local"}, format="json", **self.auth())
        repeated = self.client.post(f"/api/fault-experiments/v1/{experiment.pk}/repeat/", {"environment": "local"}, format="json", **self.auth())

        self.assertEqual(ordinary.status_code, 403)
        self.assertEqual(created.status_code, 201)
        self.assertEqual(history.data["results"][0]["id"], str(experiment.pk))
        self.assertEqual(stopped.status_code, 200)
        self.assertEqual(repeated.status_code, 200)

    def test_evaluation_list_and_overview_enrichment_do_not_expose_artifacts(self) -> None:
        feature = self.feature()
        decision = DetectionDecision.objects.create(
            feature=feature, environment="local", service="orders-api", detector_type="static_threshold",
            detector_version="1.0.0", configuration_version="static.default.v1", score=2.0,
            threshold=1.0, is_anomaly=True, severity="critical", reasons=["static.error_rate.critical"],
        )
        experiment = self.experiment()
        evaluation = DetectorEvaluation.objects.create(
            experiment=experiment, detector_type="static_threshold", detector_version="1.0.0",
            configuration_version="static.default.v1", true_positive=1, false_positive=0,
            true_negative=2, false_negative=0, precision=1, recall=1, f1_score=1, false_positive_rate=0,
            detection_delay_seconds=0, recovery_delay_seconds=300,
        )

        evaluations = self.client.get("/api/evaluations/v1/", self.scope(), **self.auth())
        overview = self.client.get("/api/telemetry/v1/overview/", {"environment": "local"}, **self.auth())

        self.assertEqual(evaluations.status_code, 200)
        self.assertEqual(evaluations.data["results"][0]["id"], str(evaluation.pk))
        self.assertEqual(overview.data["schema_version"], "overview.v2")
        self.assertEqual(overview.data["highest_anomaly_score"], {"service": "orders-api", "score": 2 / 3, "raw_score": 2.0, "severity": "critical"})
        self.assertEqual(overview.data["active_fault_count"], 1)
        self.assertEqual(overview.data["recovering_fault_count"], 0)
        self.assertTrue(overview.data["fault_context_available"])
        self.assertEqual(overview.data["latest_fault"]["id"], str(experiment.pk))
        self.assertNotIn("artifact_path", overview.data)
