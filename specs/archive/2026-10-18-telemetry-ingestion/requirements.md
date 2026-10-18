---
slug: telemetry-ingestion
title: Telemetry ingestion and minute aggregation
author: Yasin Serhat Peker
area: telemetry
status: done
verification: full
created: 2026-10-18 17:20
updated: 2026-10-18 17:48
branches: core-development
---

# Telemetry ingestion and minute aggregation

## Problem

The local demo emits OpenTelemetry signals to the Collector, but SentinelAI has no
versioned application contract for accepting telemetry, retaining it safely, or producing
the time-window summaries required by the first dashboard and later anomaly experiments.

## Scope

**In:** a token-protected, versioned telemetry batch endpoint; boundary validation and
normalization; durable raw metric events in PostgreSQL; duplicate-delivery protection;
an idempotent Celery minute-aggregation task; and a locally scheduled aggregation worker.

**Out:** a Vue dashboard, anomaly scoring, incident generation, fault-injection controls,
external benchmark imports, production deployment, and direct ingestion of the OTLP wire
protocol.

**Existing behaviour preserved:** health and order demo endpoints, static demo-token
authentication, local Docker topology, and OpenTelemetry Collector debug export.

## Acceptance criteria

- [x] A valid bounded `telemetry.v1` metric batch authenticated with the demo token is
      accepted, normalized, and stored with source and ingestion UTC timestamps. → `auto:test`
- [x] Malformed, oversized, unsupported-version, stale/future-dated, or unauthorized
      telemetry is rejected with a stable error shape and no persisted partial batch. → `auto:test`
- [x] Re-delivery of the same `event_id` is safe and does not create a second raw event. → `auto:test`
- [x] A deterministic minute aggregation records count, minimum, maximum, average, last,
      p50, p95, and p99 for an eligible metric scope and can be retried safely. → `auto:test`
- [x] The local Compose runtime starts the periodic aggregation component and the existing
      demo test suite remains green. → `auto:compose-test`
- [x] A local authenticated API walkthrough demonstrates ingestion followed by a persisted
      minute aggregate. → `manual:api`

## Affected areas

| Area | Planned change |
|---|---|
| `backend/` | Telemetry contract, validation/normalization services, raw-event and aggregate models, Celery task, API route and tests. |
| `docker-compose.yml` | Add a local Celery Beat scheduler for periodic aggregation. |
| `telemetry/` | Document the boundary between Collector OTLP intake and the Sentinel telemetry envelope. |
| `docs/` | Add a concise telemetry-envelope and local retention reference when the implementation is approved. |

## Open questions

None. Retention and the `telemetry.v1` boundary were confirmed on 2026-10-18.
