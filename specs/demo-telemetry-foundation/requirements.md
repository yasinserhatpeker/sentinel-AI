---
slug: demo-telemetry-foundation
title: Demo telemetry foundation
author: Yasin Serhat Peker
area: platform
status: active
verification: full
created: 2026-10-18 16:11
updated: 2026-10-18 16:25
branches: feature/telemetry-demo-foundation
---

# Demo telemetry foundation

## Problem

SentinelAI has a documented telemetry design but no runnable demo system that produces
the HTTP, runtime, database and queue signals required by the 29 October milestone.

## Scope

**In:** Monorepo root layout; local Docker Compose environment; Django REST demo API;
PostgreSQL, Redis and Celery Worker dependencies; `orders` and `report` demo flow;
simple demo-token authentication; OpenTelemetry Collector; documented minimum telemetry
emitted by the demo.

**Out:** Telemetry ingestion/persistence in SentinelAI, periodic aggregation, Vue
dashboard, anomaly detection, fault injection, LLM analysis and external-dataset
benchmark execution.

**Existing behaviour preserved:** No production environment, customer data or automatic
remediation is introduced.

## Acceptance criteria

- [x] Docker Compose starts the API, PostgreSQL, Redis, Celery Worker and OpenTelemetry Collector together. → `auto:check`
- [x] The repository has explicit monorepo boundaries for backend, frontend and telemetry tooling. → `manual:doc`
- [x] A documented demo API operation protected by a demo token creates an order, uses Redis and schedules a report task. → `manual:api`
- [x] The normal operation emits correlated OpenTelemetry request, database, Redis and worker telemetry. → `manual:api`
- [x] Collector output contains the minimum HTTP, runtime, database and queue measurements with service context. → `manual:api`
- [x] The local environment starts without embedding secrets or production payloads in source or fixtures. → `manual:api`
- [x] The required `Order` schema migration is reported, while no generated migration file is committed. → `manual:migration`

## Affected areas

| Area | Planned change |
|---|---|
| `backend/` | Django REST demo API and Celery Worker bootstrap |
| `frontend/` | Not changed in this spec |
| `telemetry/` | Collector configuration and local telemetry export |
| Root | Docker Compose, environment examples and documentation |

## Open questions

None.
