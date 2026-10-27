from __future__ import annotations

import time
import uuid
import os
import resource
import re

from django.db import connection
from django.http import JsonResponse

from .fault import active_fault
from .telemetry import publish_measurements, request_measurements


class TelemetryMiddleware:
    """Measures real Django request and recorded ORM query timings."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Compose probes keep containers observable but must not distort the
        # business-traffic telemetry displayed in SentinelAI.
        if request.path == "/health/":
            return self.get_response(request)
        started = time.perf_counter()
        cpu_started = time.process_time()
        query_start = len(connection.queries)
        fault = active_fault()
        if fault and fault["scenario"] == "latency":
            time.sleep(1.5)
        if fault and fault["scenario"] == "runtime-pressure":
            until = time.perf_counter() + 0.4
            while time.perf_counter() < until:
                pass
        try:
            response = JsonResponse({"error": "injected_failure"}, status=503) if fault and fault["scenario"] == "errors" and request.path != "/health/" else self.get_response(request)
        except Exception:
            self._publish(request, 500, started, cpu_started, query_start)
            raise
        self._publish(request, response.status_code, started, cpu_started, query_start)
        return response

    def _publish(self, request, status_code, started, cpu_started, query_start):
        queries = connection.queries[query_start:]
        query_duration_ms = sum(float(query.get("time", 0)) for query in queries) * 1000
        service = os.environ.get("SENTINEL_SERVICE_NAME", "")
        if service:
            duration_ms = (time.perf_counter() - started) * 1000
            cpu_percent = min(100.0, ((time.process_time() - cpu_started) * 1000 / max(duration_ms, 1)) * 100)
            memory_mb = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024
            # The ingestion schema intentionally rejects raw URL values. Keep a
            # bounded, route-like technical label that cannot contain query or
            # identifier data (for example, /v1/orders/ -> v1.orders).
            route = re.sub(r"[^a-zA-Z0-9_.-]", ".", request.path.strip("/"))[:64].strip(".") or "root"
            correlation_id = request.headers.get("X-Correlation-ID", "")
            dimensions = {"route": route, "status_class": f"{status_code // 100}xx"}
            if re.fullmatch(r"[a-f0-9-]{36}", correlation_id):
                dimensions["correlation_id"] = correlation_id
            publish_measurements(service, uuid.uuid4().hex, request_measurements(status_code, duration_ms, query_duration_ms, len(queries), cpu_percent, memory_mb), dimensions)
