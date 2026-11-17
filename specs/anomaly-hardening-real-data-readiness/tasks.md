---
slug: anomaly-hardening-real-data-readiness
title: Anomaly hardening and real-data model readiness
author: Yasin Serhat Peker
area: ml
status: active
created: 2026-11-17 16:52
updated: 2026-11-17 23:30
---

# Tasks — Anomaly hardening and real-data model readiness

## Phase 0 — Probe and gates

- [x] Read applicable repository, backend, spec and archived milestone rules.
- [x] Record the three manual-regression defects and honest-data limitations.
- [x] Confirm data, access, mutation, telemetry and operational-safety gates.
- [x] Define real-data timing and minimum-sample constraints.
- [x] Receive explicit approval for this spec and change all three files to `active` (2026-11-17).

## Phase 1 — Implement

### Package 1 — Reliability hardening

- [x] Replace container-local fault files with versioned Redis TTL state.
- [x] Keep signed local-only controls, allowlists, bounds, conflict rules and idempotent stop.
- [x] Reconcile expiry, explicit stop, service restart and watchdog database state.
- [x] Add Redis-unavailable, expiry, restart and all-fault regression tests.
- [x] Preserve raw Median/MAD evidence while producing finite normalized scores.
- [x] Add zero-dispersion, noisy, extreme, NaN/infinity and compatibility tests.
- [x] Separate active, recovering and latest-completed overview fault semantics.
- [x] Update frontend contracts and fault/anomaly presentation tests.

### Package 2 — Real-data workload and readiness

- [x] Add a bounded Docker workload runner using business HTTP endpoints only.
- [x] Cover CRUD, dependency workflow, ORM, queue production/consumption and controlled failures.
- [x] Add scoped readiness calculation for features, continuity, missingness and sequence splits.
- [x] Add Turkish readiness UI states and reproducible operator documentation.
- [x] Correct reporting queue-age semantics when broker depth is zero and add regression coverage.
- [x] Replace baseline-decision training censorship with controlled ground-truth exclusions and re-verify readiness.
- [ ] Run the workload concurrently across target services for at least the required completed-window duration.
- [ ] Verify every target service reaches 50 real `features.v2` rows without fabricated timestamps.
- [ ] Verify the LSTM target reaches at least 60 valid contiguous twelve-window journals.
- [x] Run controlled fault/recovery periods and preserve labelled evaluation windows.

### Package 3 — Model lifecycle, UI and closeout

- [ ] Train, persist, activate and live-score Isolation Forest from the collected real data.
- [ ] Train and evaluate the offline LSTM prototype from chronological splits without activation.
- [x] Present readiness, normalized scores, accurate fault state and model results in the Turkish UI.
- [ ] Execute the full API/UI/restart/fault/model manual regression and leave no unfinished fault.
- [x] Run backend, demo-service, frontend, Compose and whitespace checks.
- [ ] Document evidence, complete archive gates and archive the spec.

## Phase 2 — Verification record

| Criterion | Tag | Evidence |
|---|---|---|
| Fault TTL, stop, expiry and restart recovery | `auto:test` | Passed: 6 shared fault tests, 8 Django lifecycle tests, real 537.9→25.5 ms restart recovery and four real fault scenarios, 2026-11-17. |
| Score and overview correctness | `auto:test` | Passed in targeted 17-test suite, full 55-test backend suite, 4 frontend tests and production build, 2026-11-17. |
| Real workload and readiness | `auto:test` | Implemented bounded business-only workload, scoped readiness API/UI and operator guide; initial smoke completed 12 cycles/132 requests and the long run reached 561 successful requests with zero failures before Docker restart. Restart-safe generated run IDs prevent duplicate business records. |
| Isolation Forest lifecycle on real data | `manual:api` | Pending data collection. |
| Offline LSTM on real sequences | `manual:api` | Explicit super-admin endpoint and Turkish UI result panel implemented; activation is forbidden by contract. Real-data run remains pending the 60-sequence gate. |
| Full operator regression | `manual:ui` | Overview, service health, anomaly evidence, fault history and model-readiness screens passed manual UI verification. Analysis endpoints returned 200; model gates returned explicit 409 reason codes; real fault start→recovering→completed left zero unfinished faults. Model-success rows remain pending real-data gates. |
| Final automated regression | `auto:check` | Passed: 65 Django tests, 3 reporting-service tests, 6 shared fault tests, 4 workload tests, 4 frontend tests, production frontend build, Compose config and `git diff --check`, 2026-11-17. |
| Reporting queue-age false-positive repair | `auto:test` + `manual:data` | Passed: broker depth `0` now yields queue age `0.0`; orphaned job `2819` was requeued through the real Celery worker and completed; latest live queue-age events are bounded at `0.0`/`0.038226` seconds; all five services report 51–57 eligible real Isolation Forest samples. Regression passed: 65 Django, 3 reporting-service, 6 shared-fault, 4 workload and 4 frontend tests plus production build, Compose config and whitespace check, 2026-11-17. |

- [x] Record every automatic command result.
- [ ] Confirm the commit trailer uses `Spec: anomaly-hardening-real-data-readiness`.
