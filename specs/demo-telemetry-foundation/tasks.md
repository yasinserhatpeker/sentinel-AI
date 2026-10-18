---
slug: demo-telemetry-foundation
title: Demo telemetry foundation
author: Yasin Serhat Peker
area: platform
status: active
created: 2026-10-18 16:11
updated: 2026-10-18 16:25
---

# Tasks — Demo telemetry foundation

## Phase 0 — Probe and gates

- [x] Read the project milestone, current architecture and applicable spec rules.
- [x] Record the local synthetic-data and telemetry-privacy decisions.
- [x] Confirm the local demo API authentication mode: simple token from local configuration.
- [x] Confirm the demo domain: orders and report jobs.
- [x] Record Docker and Django verification results after dependencies exist; frontend is intentionally deferred to its dashboard spec.

## Phase 1 — Implement

- [x] Add monorepo directories and explicit backend/frontend contract boundaries.
- [x] Add local Docker Compose services for API, PostgreSQL, Redis, Celery Worker and Collector.
- [x] Build the demo-token-protected order flow and report task.
- [x] Instrument HTTP, PostgreSQL, Redis, Celery and runtime signals with OpenTelemetry.
- [x] Configure Collector intake and a local inspectable export.
- [x] Document startup, demo request and signal-inspection commands.

## Phase 2 — Verification record

| Criterion | Tag | Evidence |
|---|---|---|
| Docker Compose starts the local topology | `auto:check` | 2026-10-18: `docker compose --env-file .env.example config -q` passed; `up -d --build --force-recreate` started all five services. |
| Demo operation crosses database, cache and worker | `manual:api` | 2026-10-18: public `GET /api/health/` returned 200; an authenticated `POST /api/orders/` returned 201 and worker logs recorded successful report execution. Missing token returned stable 401. |
| Correlated telemetry is observable | `manual:api` | 2026-10-18: Collector output contained a Django server span plus child PostgreSQL and Redis spans for the order request, and Celery worker activity. |
| Minimum metrics are present | `manual:api` | 2026-10-18: Collector output contained `http.server.duration`, `process.memory.usage`, PostgreSQL spans, and `sentinel.queue.depth`, enqueue and dequeue counters. |
| Local configuration contains no secrets or production payloads | `manual:api` | 2026-10-18: `.env.example` contains local placeholders only; source and fixtures contain no production payload. |
| Migration handling is source-clean | `manual:migration` | 2026-10-18: `Order` migration requirement is recorded in design; Docker generated `demo.0001_initial` in named `local_migrations` volume and no generated migration file exists in Git source. |

- [x] Record every automatic command result.
- [ ] Confirm the proposed commit trailer uses `Spec: demo-telemetry-foundation` after user approves a commit.
