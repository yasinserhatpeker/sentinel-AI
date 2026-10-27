---
slug: service-dependency-workflow
title: Order-driven service dependency workflow
author: Yasin Serhat Peker
area: platform
status: draft
created: 2026-10-27 15:30
updated: 2026-10-27 15:30
---

# Tasks — Order-driven service dependency workflow

## Phase 0 — Probe and gates

- [x] Read applicable project, backend and spec rules.
- [x] Record data ownership, query visibility, mutation/audit, telemetry/privacy and operational
  safety decisions in `design.md`.
- [x] Record the existing independent-service and per-service-worker baseline.

## Phase 1 — Implement

- [ ] Add a bounded shared internal HTTP client with correlation propagation.
- [ ] Add idempotent downstream workflow commands and owned records where needed.
- [ ] Change orders worker from isolated completion to ordered dependency workflow orchestration.
- [ ] Capture bounded correlation context in real service telemetry.
- [ ] Add task retry, timeout and dependency-failure handling.
- [ ] Add unit and integration coverage for initial execution, duplicate retry and dependency failure.
- [ ] Update local workflow operator documentation.

## Phase 2 — Verification record

| Criterion | Tag | Evidence |
|---|---|---|
| Correlated five-service order flow | `auto:integration-test` | Pending implementation. |
| Idempotent retry behaviour | `auto:test` | Pending implementation. |
| Failure-safe task behaviour | `auto:test` | Pending implementation. |
| Local Compose walkthrough | `manual:compose` | Pending implementation. |
| Operator documentation | `manual:docs` | Pending implementation. |

- [ ] Record every automatic command result.
- [ ] Confirm the commit trailer uses `Spec: service-dependency-workflow` after commit approval.
