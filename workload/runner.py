"""Bounded real-business workload for continuous local telemetry collection."""

from __future__ import annotations

from dataclasses import dataclass
import json
import os
import random
import time
import urllib.error
import urllib.request
import uuid


SERVICE_URLS = {
    "orders-api": "http://orders-api:8080/v1",
    "payments-api": "http://payments-api:8080/v1",
    "inventory-api": "http://inventory-api:8080/v1",
    "notifications-api": "http://notifications-api:8080/v1",
    "reporting-worker": "http://reporting-worker:8080/v1",
}


@dataclass(frozen=True)
class WorkloadConfig:
    duration_seconds: int
    interval_seconds: float
    request_timeout_seconds: float
    seed: int
    run_id: str

    @classmethod
    def from_environment(cls) -> "WorkloadConfig":
        duration = int(os.environ.get("WORKLOAD_DURATION_SECONDS", "28800"))
        interval = float(os.environ.get("WORKLOAD_INTERVAL_SECONDS", "30"))
        timeout = float(os.environ.get("WORKLOAD_REQUEST_TIMEOUT_SECONDS", "5"))
        seed = int(os.environ.get("WORKLOAD_SEED", "42"))
        run_id = os.environ.get("WORKLOAD_RUN_ID") or f"run-{int(time.time())}"
        if not 60 <= duration <= 43200:
            raise ValueError("workload_duration_out_of_range")
        if not 5 <= interval <= 300:
            raise ValueError("workload_interval_out_of_range")
        if not 1 <= timeout <= 15:
            raise ValueError("workload_timeout_out_of_range")
        if not 0 <= seed <= 2_147_483_647:
            raise ValueError("workload_seed_out_of_range")
        if not run_id or len(run_id) > 48 or not all(character.isalnum() or character in "-_" for character in run_id):
            raise ValueError("workload_run_id_invalid")
        return cls(duration, interval, timeout, seed, run_id)


def request_json(method: str, url: str, *, timeout: float, body: dict | None = None) -> dict | list | None:
    encoded = json.dumps(body).encode() if body is not None else None
    headers = {"Content-Type": "application/json"} if encoded else {}
    request = urllib.request.Request(url, data=encoded, headers=headers, method=method)
    with urllib.request.urlopen(request, timeout=timeout) as response:
        if response.status == 204:
            return None
        return json.loads(response.read())


class WorkloadRunner:
    """Invokes only business endpoints; telemetry remains instrumentation-owned."""

    def __init__(self, config: WorkloadConfig) -> None:
        self.config = config
        self.random = random.Random(config.seed)
        self.success_count = 0
        self.failure_count = 0

    def _request(self, method: str, service: str, path: str, body: dict | None = None):
        try:
            result = request_json(
                method,
                f"{SERVICE_URLS[service]}{path}",
                timeout=self.config.request_timeout_seconds,
                body=body,
            )
            self.success_count += 1
            return result
        except (OSError, urllib.error.HTTPError, json.JSONDecodeError) as error:
            self.failure_count += 1
            print(json.dumps({"event": "request_failed", "service": service, "method": method, "error": type(error).__name__}), flush=True)
            return None

    def _suffix(self, cycle: int, name: str) -> str:
        identity = uuid.uuid5(uuid.NAMESPACE_URL, f"sentinelai:{self.config.run_id}:{self.config.seed}:{cycle}:{name}")
        return identity.hex[:16]

    def tick(self, cycle: int) -> None:
        suffix = self._suffix(cycle, "business")
        total = f"{self.random.randint(1000, 25000) / 100:.2f}"

        order_reference = f"load-order-{suffix}"
        order = self._request("POST", "orders-api", "/orders/", {"reference": order_reference, "total": total})
        if isinstance(order, dict):
            self._request("GET", "orders-api", f"/orders/{order_reference}/")
            self._request("PATCH", "orders-api", f"/orders/{order_reference}/", {"total": total})

        sku = f"load-sku-{suffix}"
        stock = self._request("POST", "inventory-api", "/stock/", {"sku": sku, "available_quantity": self.random.randint(5, 100)})
        if isinstance(stock, dict):
            self._request("GET", "inventory-api", f"/stock/{sku}/")

        authorization_reference = f"load-auth-{suffix}"
        authorization = self._request("POST", "payments-api", "/authorizations/", {"reference": authorization_reference, "order_reference": order_reference, "amount": total})
        if isinstance(authorization, dict):
            self._request("GET", "payments-api", f"/authorizations/{authorization_reference}/")

        notification = self._request("POST", "notifications-api", "/notifications/", {"recipient_reference": f"recipient-{suffix}", "channel": "email"})
        if isinstance(notification, dict) and notification.get("id") is not None:
            self._request("GET", "notifications-api", f"/notifications/{notification['id']}/")

        report = self._request("POST", "reporting-worker", "/reports/", {"report_type": "readiness-workload"})
        if isinstance(report, dict) and report.get("id") is not None:
            self._request("GET", "reporting-worker", f"/reports/{report['id']}/")

        print(json.dumps({"event": "workload_tick", "cycle": cycle, "success_count": self.success_count, "failure_count": self.failure_count}), flush=True)

    def run(self) -> int:
        started = time.monotonic()
        deadline = started + self.config.duration_seconds
        cycle = 0
        print(json.dumps({"event": "workload_started", "run_id": self.config.run_id, "duration_seconds": self.config.duration_seconds, "interval_seconds": self.config.interval_seconds}), flush=True)
        while time.monotonic() < deadline:
            cycle += 1
            tick_started = time.monotonic()
            self.tick(cycle)
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                break
            time.sleep(min(max(0.0, self.config.interval_seconds - (time.monotonic() - tick_started)), remaining))
        print(json.dumps({"event": "workload_completed", "cycles": cycle, "success_count": self.success_count, "failure_count": self.failure_count}), flush=True)
        return 0 if self.success_count > 0 else 1


def main() -> None:
    raise SystemExit(WorkloadRunner(WorkloadConfig.from_environment()).run())


if __name__ == "__main__":
    main()
