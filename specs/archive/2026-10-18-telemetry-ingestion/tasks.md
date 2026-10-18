---
slug: telemetry-ingestion
title: Telemetry ingestion and minute aggregation
author: Yasin Serhat Peker
area: telemetry
status: done
created: 2026-10-18 17:20
updated: 2026-10-18 17:48
---

# Tasks — Telemetry ingestion and minute aggregation

## Phase 0 — Probe and gates

- [x] Read applicable rules, milestone material, Collector configuration, and demo foundation.
- [x] Record the proposed contract and all blocking decisions in `design.md`.
- [x] Confirm local retention, ingestion scope/authentication, contract boundary, and retry/
      rollback assumptions with the requester (2026-10-18).
- [x] Record verification baselines after approval.

## Phase 1 — Implement

- [x] Add the bounded `telemetry.v1` serializer and stable error contract.
- [x] Add distinct validation, normalization, and persistence services with duplicate-event
      protection.
- [x] Add raw telemetry and aggregate model state, documenting ownership and retention.
- [x] Add a retry-safe minute aggregation task and local Celery Beat schedule.
- [x] Add ingestion, malformed input, duplicate delivery, scope, aggregate-boundary, and
      retry tests.
- [x] Document the telemetry envelope and Collector integration boundary.

## Phase 2 — Verification record

| Criterion | Tag | Evidence |
|---|---|---|
| Valid ingestion and normalization | `auto:test` | `docker compose --env-file .env.example exec --no-TTY api python manage.py test demo` — 9 tests passed, 2026-10-18. |
| Invalid/unauthorized input denial | `auto:test` | Same 9-test run; malformed and missing-token cases passed, 2026-10-18. |
| Duplicate delivery safety | `auto:test` | Same 9-test run; repeated `event_id` is stored once, 2026-10-18. |
| Deterministic aggregation and retry safety | `auto:test` | Same 9-test run; minute upsert and percentile checks passed, 2026-10-18. |
| Local Docker runtime and demo suite | `auto:compose-test` | `docker compose --env-file .env.example up --detach --build --wait` then test command passed; `down --volumes --remove-orphans` completed, 2026-10-18. |
| Local API walkthrough | `manual:api` | Authenticated `POST /api/telemetry/v1/` returned `accepted: 1`; explicit minute aggregation persisted one matching aggregate, 2026-10-18. |

- [x] Record every automatic command result.
- [x] Confirm `4e738d3` uses the trailer `Spec: telemetry-ingestion`.
