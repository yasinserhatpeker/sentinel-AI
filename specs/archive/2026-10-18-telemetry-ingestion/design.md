---
slug: telemetry-ingestion
title: Telemetry ingestion and minute aggregation
author: Yasin Serhat Peker
area: telemetry
status: done
created: 2026-10-18 17:20
updated: 2026-10-18 17:48
---

# Design — Telemetry ingestion and minute aggregation

## Approach

SentinelAI will accept a bounded JSON batch using a versioned `telemetry.v1` envelope.
The Django REST boundary authenticates the existing local demo token and validates batch
size, fields, UTC timestamps, dimensions, and schema version before it calls a separate
normalizer. The normalizer produces a canonical metric event, and persistence inserts raw
events using `event_id` as an idempotency key. The request path does not aggregate, call an
LLM, or run detection.

A retry-safe Celery task processes completed one-minute UTC windows. It groups raw numeric
metric events by environment, service, instance, deployment, metric name, unit, and safe
dimension fingerprint. It writes a single aggregate per group/window with count, min, max,
average, last value, p50, p95, and p99. A Celery Beat service schedules the task locally.
The implementation will use deterministic fixtures and an explicit watermark so a retry or
out-of-order execution cannot duplicate aggregates.

The OpenTelemetry Collector remains the local OTLP receiver and signal-observation
boundary. Native OTLP decoding is deliberately not placed in the Django request path in
this increment. A later spec may add a Collector exporter/adapter that maps OTLP signals to
the same `telemetry.v1` contract.

## Blocking decisions

### Data ownership and retention

- Status: `confirmed`
- Scope, source and retention/deletion behaviour: local synthetic telemetry only. Raw telemetry is retained for 30 days,
  then deleted by an explicit retention task introduced with the implementation; derived
  aggregates are retained until a later retention policy is approved.
- Migration required: yes, additive and reversible; no data migration. Migration files are
  generated only in the local Docker environment and are never committed.

### Authentication and query visibility

- Status: `confirmed`
- Access mode and scope: the existing static demo token authorizes ingestion in the local Docker
  environment. Write scope is fixed to `environment=local`; future read APIs must require
  explicit environment, service, and time-range scope.
- Denial behaviour: absent/invalid token is denied; malformed or unauthorized scope fails
  closed using the established stable error response shape.

### Mutation, audit and logging

- Status: `confirmed`
- State-changing paths: raw-event insertion and aggregate upsert only; no incident mutation
  or user-visible audit surface is introduced.
- Audit and safe logging decision: record event IDs, correlation/trace IDs, schema version,
  bounded field names, and aggregate window identifiers; never log raw payloads, tokens, or
  sensitive dimensions.

### Telemetry contract and privacy

- Status: `confirmed`
- Schema/version and cardinality controls: `telemetry.v1` is a JSON envelope with a maximum batch size and per-event size.
  Every event has `event_id`, `observed_at`, `metric.name`, numeric `metric.value`, optional
  `unit`, and a context containing `environment`, `service`, `instance`, optional
  `deployment_id`, and optional `trace_id`. Dimensions use an allowlist and bounded values;
  raw request paths and user identifiers are forbidden.
- Redaction and external-egress decision: local synthetic data only; no external egress,
  LLM call, or production payload is permitted.

### Operational safety

- Status: `confirmed`
- Retry/idempotency, fault-injection controls and rollback: aggregation uses a two-minute lateness watermark, upserts are unique by
  window and scope, task retries are idempotent, and an explicit local `docker compose down
  --volumes` resets demo data. Fault injection remains disabled and out of scope.

## Probe findings

- `docs/MILESTONES.md` — the 29 October delivery requires ingestion API and aggregation;
  anomaly detection begins on 12 November.
- `specs/demo-telemetry-foundation/design.md` — Collector-to-storage is explicitly deferred
  to the next spec.
- `backend/.ai/backend-conventions.md` — boundary validation, normalization, persistence,
  and asynchronous work must be separated.
- `backend/.ai/testing.md` — duplicate delivery, retry behaviour, fixed-UTC aggregation,
  scope, and malformed input need direct tests.
- `telemetry/collector-config.yaml` — current Collector receives OTLP and emits debug output;
  it contains no application-storage exporter.

## Rejected alternatives

| Option | Why not |
|---|---|
| Decode the OTLP wire protocol in Django now | Couples the application API to Collector transport details and expands the first ingestion contract beyond the dashboard milestone. |
| Aggregate in the HTTP request | Increases ingest latency and makes retry/out-of-order delivery unsafe. |
| Store arbitrary labels or raw request paths | Creates unbounded cardinality and privacy risk. |
| Build anomaly scoring in the same increment | The milestone sequence reserves scoring and fault evaluation for the anomaly-detection phase. |

## API and data contract

- Endpoint(s): one local token-protected write-only endpoint under `/api/telemetry/v1/`;
  the exact trailing route and response fields will be frozen with serializer tests.
- Event/schema fields: envelope version and bounded event list; canonical event ID, observed
  timestamp, ingestion timestamp, metric name/value/unit, environment, service, instance,
  deployment ID, trace ID, and allowlisted dimensions.
- Query parameters and response shape: this increment has no public telemetry query API.
  Dashboard read endpoints are a separate contract.
- Compatibility: existing demo routes remain unchanged. Future OTLP adapters must emit the
  same canonical `telemetry.v1` fields or introduce an explicitly versioned successor.

## Impact analysis

- Changed: backend data model, Celery schedule, local Compose topology, telemetry contract
  documentation, and automated backend coverage.
- Possibly affected: upcoming dashboard, detector, incident, and benchmark pipelines consume
  aggregate windows and must respect their scope/dimension contract.
- Risk: high-cardinality dimensions, late-arriving events, and percentile calculation cost.
- Recommendation: use this completed write and aggregation foundation before adding dashboard
  reads or Collector export adapters.

## Decision log

| Date | Decision | Why |
|---|---|---|
| 2026-10-18 | Separate validated JSON envelope from native OTLP transport | Makes the first storage contract versioned, bounded, and directly testable. |
| 2026-10-18 | Aggregate on one-minute UTC windows through Celery | Supplies dashboard/ML-ready features without slowing ingestion. |
| 2026-10-18 | Keep dashboard and anomaly logic out of this spec | Preserves the dependency order in the 29 October and 12 November milestones. |
| 2026-10-18 | Confirm 30-day local raw retention and `telemetry.v1` as the first storage contract | User approval for the active spec. |

## Rules consulted

- `AGENTS.md`
- `specs/README.md`
- `backend/.ai/backend-conventions.md`
- `backend/.ai/basemodel-audit.md`
- `backend/.ai/drf-viewsets.md`
- `backend/.ai/queryset-authorization.md`
- `backend/.ai/testing.md`
