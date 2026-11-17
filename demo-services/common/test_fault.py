import json
import os
import unittest
from unittest.mock import patch

import redis

from . import fault


class InMemoryRedis:
    def __init__(self) -> None:
        self.values: dict[str, str] = {}
        self.expiries: dict[str, int] = {}
        self.available = True

    def _ensure_available(self) -> None:
        if not self.available:
            raise redis.ConnectionError("unavailable")

    def get(self, key: str):
        self._ensure_available()
        return self.values.get(key)

    def set(self, key: str, value: str, *, ex: int, nx: bool):
        self._ensure_available()
        if nx and key in self.values:
            return False
        self.values[key] = value
        self.expiries[key] = ex
        return True

    def delete(self, key: str) -> int:
        self._ensure_available()
        existed = key in self.values
        self.values.pop(key, None)
        self.expiries.pop(key, None)
        return int(existed)

    def eval(self, _script: str, _key_count: int, key: str, expected: str) -> int:
        self._ensure_available()
        if self.values.get(key) != expected:
            return 0
        return self.delete(key)


class FaultStateTests(unittest.TestCase):
    def setUp(self) -> None:
        self.store = InMemoryRedis()
        self.environment = patch.dict(
            os.environ,
            {"SENTINEL_SERVICE_NAME": "orders-api", "REDIS_URL": "redis://test:6379/0"},
        )
        self.client_patch = patch.object(fault, "_redis_client", return_value=self.store)
        self.environment.start()
        self.client_patch.start()

    def tearDown(self) -> None:
        self.client_patch.stop()
        self.environment.stop()

    def payload(self, experiment_id="00000000-0000-0000-0000-000000000001"):
        return {"scenario": "latency", "duration_seconds": 60, "experiment_id": experiment_id, "seed": 42, "parameters": {"delay_ms": 500}}

    def test_start_retry_stop_and_conflict(self) -> None:
        first = fault.start_fault(self.payload())
        retry = fault.start_fault(self.payload())
        self.assertEqual(first["experiment_id"], retry["experiment_id"])
        self.assertEqual(first["schema_version"], "fault-state.v1")
        self.assertEqual(first["service"], "orders-api")
        self.assertEqual(self.store.expiries[fault._fault_key()], 60)
        with self.assertRaisesRegex(ValueError, "fault_conflict"):
            fault.start_fault(self.payload("00000000-0000-0000-0000-000000000002"))
        self.assertTrue(fault.stop_fault(first["experiment_id"]))
        self.assertFalse(fault.stop_fault(first["experiment_id"]))

    def test_expired_state_recovers_automatically(self) -> None:
        with patch("common.fault.time.time", return_value=1000):
            fault.start_fault(self.payload())
        with patch("common.fault.time.time", return_value=1061):
            self.assertIsNone(fault.active_fault())
        self.assertNotIn(fault._fault_key(), self.store.values)

    def test_process_restart_clears_shared_fault_state(self) -> None:
        fault.start_fault(self.payload())
        self.assertIsNotNone(fault.active_fault())
        fault.clear_fault_on_startup()
        self.assertIsNone(fault.active_fault())

    def test_runtime_fails_open_but_control_mutation_fails_closed(self) -> None:
        fault.start_fault(self.payload())
        self.store.available = False
        self.assertIsNone(fault.active_fault())
        with self.assertRaisesRegex(fault.FaultStateUnavailable, "fault_state_unavailable"):
            fault.start_fault(self.payload())
        with self.assertRaisesRegex(fault.FaultStateUnavailable, "fault_state_unavailable"):
            fault.stop_fault(self.payload()["experiment_id"])

    def test_invalid_or_cross_service_state_is_discarded(self) -> None:
        key = fault._fault_key()
        self.store.values[key] = "not-json"
        self.assertIsNone(fault.active_fault())
        self.store.values[key] = json.dumps(
            {
                **self.payload(),
                "schema_version": fault.FAULT_SCHEMA_VERSION,
                "service": "payments-api",
                "started_at": 1000,
                "expires_at": 2000,
            }
        )
        self.assertIsNone(fault.active_fault())

    def test_unsafe_parameters_are_rejected(self) -> None:
        payload = self.payload()
        payload["parameters"] = {"delay_ms": 9000}
        with self.assertRaisesRegex(ValueError, "fault_delay_out_of_range"):
            fault.start_fault(payload)


if __name__ == "__main__":
    unittest.main()
