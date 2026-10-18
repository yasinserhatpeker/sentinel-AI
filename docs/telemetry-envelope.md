# Telemetry envelope v1

SentinelAI accepts local synthetic metric events through `POST /api/telemetry/v1/`.
The endpoint uses the existing `Authorization: Demo <token>` demo authentication and is
not a public or production ingestion endpoint.

## Envelope

```json
{
  "schema_version": "telemetry.v1",
  "events": [
    {
      "event_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
      "observed_at": "2026-10-18T14:30:10Z",
      "metric": {"name": "http.server.duration", "value": 42.3, "unit": "ms"},
      "context": {
        "environment": "local",
        "service": "sentinel-demo-api",
        "instance": "api-1",
        "deployment_id": "demo-1",
        "trace_id": "0123456789abcdef"
      },
      "dimensions": {"route": "orders.create", "status_class": "2xx"}
    }
  ]
}
```

Each batch contains 1–100 events. Event IDs make delivery idempotent. Timestamps are UTC
and must be within seven days in the past or five minutes in the future. Dimension values
are bounded and must never include user IDs, raw request paths, tokens, or other sensitive
data.

## Storage and aggregation

Raw events are local synthetic data and are deleted after 30 days by a scheduled Celery
task. A second scheduled task aggregates completed one-minute UTC windows by metric scope.
Each aggregate stores count, minimum, maximum, average, last value, p50, p95, and p99.

The OpenTelemetry Collector continues to receive OTLP signals. An OTLP-to-envelope adapter
is intentionally a future integration: storage code depends on this bounded SentinelAI
contract rather than on a Collector transport implementation.
