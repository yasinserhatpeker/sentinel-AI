"""Bounded telemetry published from real Django request/task execution."""

from __future__ import annotations

import json
import os
import threading
import urllib.request
import uuid
import hashlib
import hmac
from datetime import UTC, datetime


def publish_measurements(service: str, trace_id: str, measurements: list[tuple[str, float, str]], dimensions: dict[str, str]) -> None:
    endpoint = os.environ.get("TELEMETRY_INGEST_URL")
    secret = os.environ.get("DJANGO_SECRET_KEY")
    if not endpoint or not secret:
        return
    context = {"environment": "local", "service": service, "instance": os.environ.get("HOSTNAME", f"{service}-local"), "deployment_id": "compose-local", "trace_id": trace_id}
    payload = {"schema_version": "telemetry.v1", "events": [{"event_id": str(uuid.uuid4()), "observed_at": datetime.now(UTC).isoformat(), "metric": {"name": name, "value": value, "unit": unit}, "context": context, "dimensions": dimensions} for name, value, unit in measurements]}

    def send() -> None:
        signature = hmac.new(secret.encode(), b"sentinelai-local-telemetry-v1", hashlib.sha256).hexdigest()
        request = urllib.request.Request(endpoint, data=json.dumps(payload).encode(), headers={"Content-Type": "application/json", "X-Telemetry-Signature": signature}, method="POST")
        try:
            with urllib.request.urlopen(request, timeout=2):
                pass
        except OSError:
            return

    threading.Thread(target=send, daemon=True).start()


def request_measurements(status_code: int, duration_ms: float, query_duration_ms: float, query_count: int, cpu_percent: float, memory_mb: float) -> list[tuple[str, float, str]]:
    # Each value is observed while handling this concrete request.  In
    # particular, query errors are deliberately not reported as a synthetic
    # zero: they are emitted only by the code path that actually fails.
    return [("http.server.request_count", 1.0, "requests"), ("http.server.error_rate", 1.0 if status_code >= 500 else 0.0, "ratio"), ("http.server.duration", duration_ms, "ms"), ("runtime.cpu.usage", cpu_percent, "percent"), ("runtime.memory.usage", memory_mb, "mb"), ("db.connection.usage", 1.0 if query_count else 0.0, "connections"), ("db.query.duration", query_duration_ms, "ms")]
