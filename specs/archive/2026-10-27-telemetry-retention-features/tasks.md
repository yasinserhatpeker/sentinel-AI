---
slug: telemetry-retention-features
title: Telemetry retention and ML feature pipeline
author: Yasin Serhat Peker
area: telemetry
status: done
created: 2026-10-27 15:45
updated: 2026-10-27 19:58
---

# Tasks — Telemetry retention and ML feature pipeline

## Phase 1 — Implement
- [x] Add feature model and deterministic five-minute materializer.
- [x] Add retention and idempotent backfill tasks/tests.
- [x] Document retention boundaries and feature contract.

## Phase 2 — Verification record

| Criterion | Tag | Evidence |
|---|---|---|
| Retention boundary | `auto:test` | `docker compose run --rm --build api python manage.py test demo.tests` — 25 tests passed on 27/10/2026 19:56. |
| Deterministic feature window | `auto:test` | Same test suite validates fixed five-minute `features.v1` rows scoped by environment/service. |
| Idempotent backfill | `auto:test` | Test suite passed; local aggregate backfill created 130 feature rows and a second run kept the row count at 130. |
