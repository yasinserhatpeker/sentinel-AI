# Telemetry envelope v1

SentinelAI accepts local metric events measured by the demo services through `POST /api/telemetry/v1/`. Browser
administrators use their short-lived `Authorization: Bearer <access-jwt>` token. The five local
demo containers instead send an `X-Telemetry-Signature` HMAC derived from the existing
`DJANGO_SECRET_KEY`. The raw secret is never sent to Vue, returned by an endpoint or logged.
This is a local development ingestion boundary, not a public production endpoint.

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

Raw events are local technical telemetry and are deleted after 30 days by a scheduled Celery
task. A second scheduled task aggregates completed one-minute UTC windows by metric scope.
Each aggregate stores count, minimum, maximum, average, last value, p50, p95, and p99.

The OpenTelemetry Collector remains the local OTLP inspection boundary. The dashboard's
validated `telemetry.v1` metrics are published to the core API through the separate scoped
machine credential: the stock Collector cannot translate arbitrary OTLP payloads into this
application-specific envelope without a dedicated adapter. This keeps the transport distinction
explicit rather than pretending that a Collector debug exporter persists dashboard data.
