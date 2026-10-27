---
slug: dashboard-foundation
title: Local telemetry dashboard foundation
author: Yasin Serhat Peker
area: frontend
status: active
verification: full
created: 2026-10-27 14:10
updated: 2026-10-27 15:22
branches: core-development
---

# Local telemetry dashboard foundation

## Problem

Telemetry events and minute aggregates can be stored locally, but operators cannot yet
discover available services, select an explicit analysis scope, or visualize service
health and metric trends. The 29 October milestone also requires a first Vue dashboard,
not only backend telemetry storage.

## Scope

**In:** a Vue 3 + TypeScript local dashboard; token entry held in memory only; explicit
environment/service/time-range controls; read-only aggregate/service API endpoints;
dashboard loading, empty, partial-data and error states; base charts for request volume,
error rate, latency percentiles, runtime/database/queue metrics; local Docker frontend
service; a restrained corporate green observability interface with functional, accessible
icons only; and a deterministic local telemetry demo data path for manual dashboard review.

**Out:** anomaly scoring, incident timeline, fault controls, production hosting, multi-user
authentication, local token persistence, native OTLP decoding, external datasets, and LLM
analysis.

**Existing behaviour preserved:** the token-protected order and telemetry ingestion APIs,
local-only Docker topology, raw-event retention, minute aggregation, and CI cleanup.

## Acceptance criteria

- [x] The dashboard starts through Docker Compose and can call the local API with a demo
      token that is never written to local storage. → `auto:frontend-build`
- [x] The aggregate endpoint requires environment, service, start and end scope; invalid,
      unauthorized or excessively broad requests fail with a stable error response. → `auto:test`
- [x] The dashboard shows service health, request volume, error rate, p50/p95/p99 latency,
      and available runtime/database/queue series for the selected scope. → `manual:ui`
- [x] Loading, empty-data, partial-data and API-error states are visible and accessible. → `auto:frontend-test`
- [x] A deterministic local telemetry walkthrough produces data visible in the dashboard. → `manual:ui`
- [x] The full Compose topology, backend test suite and frontend build complete successfully. → `auto:compose-test`

## Affected areas

| Area | Planned change |
|---|---|
| `backend/demo/` | Read-only aggregate and service-discovery contract, serializers, scope validation and tests. |
| `frontend/` | Vite/Vue application, typed API service, session-only token state, dashboard view and accessible chart components. |
| `docker-compose.yml` | Local dashboard container and frontend environment wiring. |
| `docs/` | Local dashboard walkthrough and API contract examples. |
| `specs/` | Approved dashboard contract, implementation tasks and verification evidence. |

## Open questions

None. Resolved 2026-10-27: the requester approved memory-only demo-token entry, explicit
scope selection, HTTP/runtime/database/queue metric groups, local Docker delivery and the
restrained corporate-green interface direction.
