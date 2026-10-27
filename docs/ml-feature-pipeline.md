# Telemetry retention and ML feature pipeline

SentinelAI keeps three local telemetry layers with distinct purposes:

| Layer | Contents | Retention | Consumer |
| --- | --- | --- | --- |
| Raw events | Normalized, bounded telemetry events | 30 days | Investigation and minute aggregation |
| Minute aggregates | Numeric summaries per metric/service/instance | Until local environment reset | Dashboard and feature materializer |
| `features.v1` | Fixed five-minute, service-scoped ML vectors | Until local environment reset | Future Isolation Forest training and scoring |

## Feature contract

Each `TelemetryFeature` row is uniquely keyed by `schema_version`, `window_start`,
`environment` and `service`. It contains aggregate-only fields: request count, error rate,
HTTP and database p95 latency, CPU/memory averages, queue depth/age, queue throughput and
failed task count. Raw dimensions, trace IDs, URLs and payloads are never copied into the
feature table.

Unavailable measurements remain `NULL`; the future detector must apply a documented
imputation policy before training or scoring. This prevents absent telemetry from being
mistaken for an observed zero.

## Operations

Celery Beat materializes the completed five-minute window every five minutes. The work uses
`update_or_create`, so retrying a task or replaying a bounded historical period is safe.

For a local backfill, call the internal task with UTC timestamps:

```python
from demo.tasks import backfill_telemetry_features

backfill_telemetry_features.delay(
    "2026-10-27T10:00:00+00:00",
    "2026-10-27T12:00:00+00:00",
)
```

Raw retention deletes only expired `TelemetryEvent` rows. It does not delete minute
aggregates or feature vectors, preserving a bounded local baseline for the next anomaly
detection increment.
