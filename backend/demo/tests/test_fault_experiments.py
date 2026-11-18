from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from demo.faults import RECOVERY_SECONDS, recover_expired_experiments, repeat_experiment, start_experiment, stop_experiment
from demo.models import FaultExperiment, GroundTruthWindow


class FaultExperimentTests(TestCase):
    def setUp(self) -> None:
        user_model = get_user_model()
        self.admin = user_model.objects.create_user(username="fault-admin", password="unused", is_superuser=True, is_staff=True)
        self.user = user_model.objects.create_user(username="fault-user", password="unused")

    @patch("demo.faults._send_control", return_value={"status": "active"})
    def test_super_admin_starts_bounded_local_experiment(self, send_control) -> None:
        experiment = start_experiment(
            actor=self.admin,
            service="payments-api",
            fault_type=FaultExperiment.FaultType.HIGH_LATENCY,
            duration_seconds=60,
            parameters={"delay_ms": 750},
            seed=42,
        )

        self.assertEqual(experiment.environment, "local")
        self.assertEqual(experiment.status, FaultExperiment.Status.ACTIVE)
        self.assertIsNotNone(experiment.started_at)
        self.assertEqual(experiment.expires_at, experiment.started_at + timedelta(seconds=60))
        payload = send_control.call_args.args[1]
        self.assertEqual(payload["scenario"], "latency")
        self.assertEqual(payload["experiment_id"], str(experiment.pk))

    def test_non_super_admin_and_unsafe_parameters_are_rejected(self) -> None:
        with self.assertRaisesMessage(PermissionError, "fault_super_admin_required"):
            start_experiment(actor=self.user, service="orders-api", fault_type=FaultExperiment.FaultType.ERROR_BURST, duration_seconds=60, parameters={"error_probability": 0.5}, seed=1)
        with self.assertRaisesMessage(ValueError, "fault_delay_out_of_range"):
            start_experiment(actor=self.admin, service="orders-api", fault_type=FaultExperiment.FaultType.HIGH_LATENCY, duration_seconds=60, parameters={"delay_ms": 6000}, seed=1)
        with self.assertRaisesMessage(ValueError, "queue_backlog_requires_reporting_worker"):
            start_experiment(actor=self.admin, service="orders-api", fault_type=FaultExperiment.FaultType.QUEUE_BACKLOG, duration_seconds=60, parameters={"delay_ms": 1000}, seed=1)

    @patch("demo.faults._send_control", return_value={"status": "active"})
    def test_conflicting_fault_is_rejected(self, _send_control) -> None:
        start_experiment(actor=self.admin, service="orders-api", fault_type=FaultExperiment.FaultType.ERROR_BURST, duration_seconds=60, parameters={"error_probability": 0.5}, seed=1)
        with self.assertRaisesMessage(ValueError, "fault_experiment_conflict"):
            start_experiment(actor=self.admin, service="orders-api", fault_type=FaultExperiment.FaultType.DATABASE_SLOWDOWN, duration_seconds=60, parameters={"delay_ms": 500}, seed=2)

    @patch("demo.faults._send_control", return_value={"status": "ok"})
    def test_stop_is_idempotent_and_materializes_ground_truth(self, _send_control) -> None:
        experiment = start_experiment(actor=self.admin, service="inventory-api", fault_type=FaultExperiment.FaultType.DATABASE_SLOWDOWN, duration_seconds=60, parameters={"delay_ms": 500}, seed=7)
        stopped = stop_experiment(experiment, now=experiment.started_at + timedelta(seconds=30))
        repeated_stop = stop_experiment(stopped, now=experiment.started_at + timedelta(seconds=40))

        self.assertEqual(stopped.status, FaultExperiment.Status.RECOVERING)
        self.assertEqual(stopped.recovery_until, stopped.stopped_at + timedelta(seconds=RECOVERY_SECONDS))
        self.assertEqual(repeated_stop.status, FaultExperiment.Status.RECOVERING)
        labels = set(stopped.ground_truth_windows.values_list("label", flat=True))
        self.assertEqual(labels, {GroundTruthWindow.Label.NORMAL, GroundTruthWindow.Label.FAULT_ACTIVE, GroundTruthWindow.Label.RECOVERING})
        self.assertEqual(stopped.ground_truth_windows.count(), GroundTruthWindow.objects.filter(experiment=stopped).count())

    @patch("demo.faults._send_control", return_value={"status": "ok"})
    def test_watchdog_recovers_expired_fault_and_completes_recovery(self, _send_control) -> None:
        experiment = start_experiment(actor=self.admin, service="reporting-worker", fault_type=FaultExperiment.FaultType.QUEUE_BACKLOG, duration_seconds=15, parameters={"delay_ms": 1000}, seed=9)
        expiry = experiment.expires_at + timedelta(seconds=1)

        self.assertEqual(recover_expired_experiments(now=expiry), 1)
        experiment.refresh_from_db()
        self.assertEqual(experiment.status, FaultExperiment.Status.RECOVERING)
        self.assertEqual(recover_expired_experiments(now=experiment.recovery_until + timedelta(seconds=1)), 1)
        experiment.refresh_from_db()
        self.assertEqual(experiment.status, FaultExperiment.Status.COMPLETED)

    @patch("demo.faults._send_control", return_value={"status": "active"})
    def test_new_experiment_self_heals_elapsed_recovery_without_watchdog(self, _send_control) -> None:
        elapsed = FaultExperiment.objects.create(
            environment="local",
            service="inventory-api",
            fault_type=FaultExperiment.FaultType.HIGH_LATENCY,
            status=FaultExperiment.Status.RECOVERING,
            parameters={"delay_ms": 500.0},
            duration_seconds=30,
            seed=10,
            created_by=self.admin,
            stopped_at=timezone.now() - timedelta(minutes=3),
            recovery_until=timezone.now() - timedelta(minutes=1),
        )

        started = start_experiment(
            actor=self.admin,
            service="inventory-api",
            fault_type=FaultExperiment.FaultType.HIGH_LATENCY,
            duration_seconds=30,
            parameters={"delay_ms": 750},
            seed=11,
        )

        elapsed.refresh_from_db()
        self.assertEqual(elapsed.status, FaultExperiment.Status.COMPLETED)
        self.assertEqual(started.status, FaultExperiment.Status.ACTIVE)

    @patch("demo.faults._send_control")
    def test_watchdog_reconciles_fault_cleared_by_service_restart(self, send_control) -> None:
        send_control.side_effect = [
            {"status": "active"},
            {"status": "idle", "experiment_id": None},
        ]
        experiment = start_experiment(
            actor=self.admin,
            service="orders-api",
            fault_type=FaultExperiment.FaultType.HIGH_LATENCY,
            duration_seconds=60,
            parameters={"delay_ms": 500},
            seed=42,
        )

        changed = recover_expired_experiments(now=experiment.started_at + timedelta(seconds=10))

        self.assertEqual(changed, 1)
        experiment.refresh_from_db()
        self.assertEqual(experiment.status, FaultExperiment.Status.RECOVERING)
        self.assertEqual(experiment.stopped_at, experiment.started_at + timedelta(seconds=10))
        self.assertGreater(experiment.ground_truth_windows.count(), 0)
        self.assertIn(GroundTruthWindow.Label.RECOVERING, set(experiment.ground_truth_windows.values_list("label", flat=True)))

    @patch("demo.faults._send_control")
    def test_watchdog_preserves_active_audit_when_service_is_temporarily_unavailable(self, send_control) -> None:
        send_control.side_effect = [{"status": "active"}, RuntimeError("fault_control_unavailable")]
        experiment = start_experiment(
            actor=self.admin,
            service="payments-api",
            fault_type=FaultExperiment.FaultType.HIGH_LATENCY,
            duration_seconds=60,
            parameters={"delay_ms": 500},
            seed=42,
        )

        self.assertEqual(recover_expired_experiments(now=experiment.started_at + timedelta(seconds=10)), 0)
        experiment.refresh_from_db()
        self.assertEqual(experiment.status, FaultExperiment.Status.ACTIVE)

    @patch("demo.faults._send_control", return_value={"status": "ok"})
    def test_repeat_reuses_parameters_and_seed(self, _send_control) -> None:
        original = start_experiment(actor=self.admin, service="notifications-api", fault_type=FaultExperiment.FaultType.ERROR_BURST, duration_seconds=30, parameters={"error_probability": 0.25}, seed=123)
        stopped = stop_experiment(original)
        stopped.status = FaultExperiment.Status.COMPLETED
        stopped.save(update_fields=("status",))

        repeated = repeat_experiment(stopped, actor=self.admin)

        self.assertEqual(repeated.repeated_from_id, original.pk)
        self.assertEqual(repeated.parameters, original.parameters)
        self.assertEqual(repeated.seed, original.seed)
