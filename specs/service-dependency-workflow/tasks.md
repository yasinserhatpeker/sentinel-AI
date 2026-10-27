---
slug: service-dependency-workflow
title: Order-driven service dependency workflow
author: Yasin Serhat Peker
area: platform
status: active
created: 2026-10-27 15:30
updated: 2026-10-27 15:45
---

# Tasks — Order-driven service dependency workflow

## Phase 0 — Probe and gates

- [x] Read applicable project, backend and spec rules.
- [x] Record data ownership, query visibility, mutation/audit, telemetry/privacy and operational
  safety decisions in `design.md`.
- [x] Record the existing independent-service and per-service-worker baseline.

## Phase 1 — Implement

- [x] Add a bounded shared internal HTTP client with correlation propagation.
- [x] Add idempotent downstream workflow commands and owned records where needed.
- [x] Change orders worker from isolated completion to ordered dependency workflow orchestration.
- [x] Capture bounded correlation context in real service telemetry.
- [x] Add task retry, timeout and dependency-failure handling.
- [~] Add unit and integration coverage for initial execution, duplicate retry and dependency failure. Manual Docker integration verification completed 27/10/2026; repository-level automated coverage remains a follow-up.
- [x] Update local workflow operator documentation.

## Phase 2 — Verification record

| Criterion | Tag | Evidence |
|---|---|---|
| Correlated five-service order flow | `auto:integration-test` | `workflow-e2e-2` completed order → payment → reservation → notification → report on 27/10/2026. |
| Idempotent retry behaviour | `auto:test` | A second task for `workflow-e2e-2` left one authorization, reservation, notification and report. |
| Failure-safe task behaviour | `auto:test` | Inventory `errors` fault produced order `failed`, zero notifications and zero reports for `workflow-failure-final`. |
| Local Compose walkthrough | `manual:compose` | All downstream workers completed their real domain work. |
| Operator documentation | `manual:docs` | `docs/local-dashboard.md` updated with workflow behaviour. |

- [x] Record every automatic command result.
- [ ] Confirm the commit trailer uses `Spec: service-dependency-workflow` after commit approval.
