---
slug: dashboard-foundation
title: Local telemetry dashboard foundation
author: Yasin Serhat Peker
area: frontend
status: active
created: 2026-10-27 14:10
updated: 2026-10-27 15:22
---

# Tasks — Local telemetry dashboard foundation

## Phase 0 — Probe and gates

- [x] Read applicable backend/frontend rules, milestone material, local topology and
      telemetry ingestion contract.
- [x] Record proposed dashboard/read-contract design and blocking decisions.
- [x] Confirm token-entry UX, metric groups and all pending gates with the requester.
- [x] Record implementation verification baselines after approval.

## Phase 1 — Implement

- [x] Add scoped service-discovery and aggregate read serializers, views, URLs and tests.
- [x] Add deterministic local telemetry sample generation/documented walkthrough.
- [x] Create the Vue 3 + TypeScript dashboard foundation with typed telemetry API service.
- [x] Add token entry held only in session memory and explicit scope controls.
- [x] Add accessible status cards and chart components for HTTP, runtime, database and queue
      aggregate groups.
- [x] Add loading, empty, partial-data and API-error states.
- [x] Add frontend Docker service and CI build/test coverage.
- [x] Document local startup, token entry, scope selection and sample telemetry walkthrough.

## Phase 2 — Verification record

| Criterion | Tag | Evidence |
|---|---|---|
| Scoped aggregate API contract | `auto:test` | `docker compose --env-file .env.example exec --no-TTY api python manage.py test demo` — 12 tests passed on 2026-10-27. |
| Frontend build and accessible view states | `auto:frontend-build` / `auto:frontend-test` | `npm run test` — 2 tests passed; `npm run build` — Vue type-check and Vite build passed on 2026-10-27. |
| Docker topology and backend tests | `auto:compose-test` | `docker compose --env-file .env.example up --detach --build --wait` reached healthy services; Django tests and dashboard build then passed on 2026-10-27. |
| Scoped local dashboard walkthrough | `manual:ui` | Verified at `http://localhost:5174` with seeded `sentinel-demo-api` data and in-memory local demo token on 2026-10-27. |

- [x] Record every automatic command result.
- [ ] Confirm the proposed commit trailer uses `Spec: dashboard-foundation` after commit approval.
