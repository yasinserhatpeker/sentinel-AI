import os
import unittest
from unittest.mock import patch

from runner import WorkloadConfig, WorkloadRunner


class WorkloadRunnerTests(unittest.TestCase):
    def config(self) -> WorkloadConfig:
        return WorkloadConfig(60, 5, 2, 42, "test-run")

    def test_configuration_is_bounded(self) -> None:
        with patch.dict(os.environ, {"WORKLOAD_DURATION_SECONDS": "59"}, clear=True):
            with self.assertRaisesRegex(ValueError, "workload_duration_out_of_range"):
                WorkloadConfig.from_environment()

    def test_empty_run_id_gets_restart_safe_generated_identity(self) -> None:
        with patch.dict(os.environ, {
            "WORKLOAD_DURATION_SECONDS": "60",
            "WORKLOAD_INTERVAL_SECONDS": "5",
            "WORKLOAD_REQUEST_TIMEOUT_SECONDS": "1",
            "WORKLOAD_SEED": "42",
            "WORKLOAD_RUN_ID": "",
        }, clear=True):
            config = WorkloadConfig.from_environment()

        self.assertRegex(config.run_id, r"^run-\d+$")

    @patch("runner.request_json")
    def test_tick_uses_real_business_endpoints_without_telemetry_writes(self, request_json) -> None:
        request_json.side_effect = [
            {"reference": "order"}, {}, {},
            {"sku": "stock"}, {},
            {"reference": "authorization"}, {},
            {"id": 1}, {},
            {"id": 2}, {},
        ]
        runner = WorkloadRunner(self.config())

        runner.tick(1)

        urls = [call.args[1] for call in request_json.call_args_list]
        self.assertEqual(len(urls), 11)
        self.assertTrue(any("orders-api:8080/v1/orders/" in url for url in urls))
        self.assertTrue(any("payments-api:8080/v1/authorizations/" in url for url in urls))
        self.assertTrue(any("inventory-api:8080/v1/stock/" in url for url in urls))
        self.assertTrue(any("notifications-api:8080/v1/notifications/" in url for url in urls))
        self.assertTrue(any("reporting-worker:8080/v1/reports/" in url for url in urls))
        self.assertFalse(any("telemetry" in url for url in urls))
        self.assertEqual(runner.success_count, 11)

    @patch("runner.request_json", side_effect=OSError("offline"))
    def test_failures_are_bounded_and_do_not_stop_other_services(self, _request_json) -> None:
        runner = WorkloadRunner(self.config())

        runner.tick(1)

        self.assertEqual(runner.success_count, 0)
        self.assertEqual(runner.failure_count, 5)


if __name__ == "__main__":
    unittest.main()
