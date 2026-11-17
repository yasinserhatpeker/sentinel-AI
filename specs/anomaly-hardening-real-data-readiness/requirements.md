---
slug: anomaly-hardening-real-data-readiness
title: Anomaly hardening and real-data model readiness
author: Yasin Serhat Peker
area: ml
status: active
verification: full
created: 2026-11-17 16:52
updated: 2026-11-17 17:00
branches: core-development
---

# Anomaly hardening and real-data model readiness

## Problem

The anomaly milestone works end to end, but manual verification exposed three reliability defects: demo-service restarts preserve stale file-backed fault state, zero-dispersion Median/MAD windows can create unbounded scores, and System Overview can describe the latest completed fault as active. The honest local dataset is also below the production-like minimum gates required to manually verify Isolation Forest activation/live scoring and the offline LSTM prototype.

## Scope

**In:** Redis TTL-backed local fault state and restart-safe recovery; bounded and comparable anomaly scores while retaining raw evidence; separate active/recovering/completed fault overview fields; a real API/ORM/queue workload runner; readiness reporting for feature counts, continuity, missingness and model gates; at least 50 real five-minute feature rows per target service; at least 60 contiguous twelve-window journals for the selected LSTM service; manual Isolation Forest training, activation and live inference; explicit offline LSTM training/evaluation; regression tests and operator documentation.

**Out:** fabricated or backdated telemetry, reduced safety thresholds, production fault injection, automatic LSTM activation, external dataset ingestion, external LLM calls, production deployment and automatic remediation.

**Existing behaviour preserved:** real demo-service business operations remain the only metric source; `telemetry.v1`, `features.v1`, `features.v2`, detector decision traceability, local-only super-admin fault controls, JWT/CSRF security, retention rules and the Turkish corporate dashboard remain compatible.

## Acceptance criteria

- [x] Fault state uses bounded Redis keys with TTL, fails open to normal service behaviour when unavailable and cannot survive expiry/stop/restart as stale active state. → `auto:test`
- [x] High-latency, error-burst, database-slowdown and queue-backlog experiments remain signed, local-only, conflict-safe and recover through stop, expiry and service restart. → `manual:api`
- [x] Median/MAD handles zero dispersion without NaN, infinity or unbounded values; decisions retain a raw technical score and expose a comparable normalized score. → `auto:test`
- [x] System Overview distinguishes active, recovering and latest completed fault information and never labels historical state as active. → `auto:test`
- [x] A bounded Docker workload runner creates real HTTP, ORM and queue activity across the dependency workflow without writing metric rows directly. → `auto:test`
- [x] Readiness reporting exposes real feature counts, contiguous-window counts, gaps, missingness, split counts and explicit Isolation Forest/LSTM readiness without raw payloads. → `auto:test`
- [ ] Every target service reaches at least 50 real `features.v2` rows with no fabricated timestamps; the selected LSTM service reaches at least 60 valid twelve-window journals. → `manual:data`
- [ ] Isolation Forest trains from real time-ordered data, persists/activates a compatible artifact and produces a traceable live decision for a later completed window. → `manual:api`
- [ ] The offline LSTM prototype trains and evaluates from chronological train/validation/test journals when the real-data gate is met and is never activated automatically. → `manual:api`
- [x] The Turkish operator UI presents normalized anomaly scores, accurate fault state and model-data readiness with loading, collecting, ready, partial and error states. → `manual:ui`
- [ ] Backend, demo-service, frontend, Compose and whitespace checks pass, followed by a full manual regression with no unfinished fault experiment. → `auto:check`

## Affected areas

| Area | Planned change |
|---|---|
| `demo-services/common/` | Replace local fault files with signed, TTL-backed Redis runtime state and safe fallback behaviour. |
| `backend/demo/faults.py`, tasks and tests | Reconcile experiment lifecycle with Redis, expiry, restart and watchdog recovery. |
| `backend/demo/detection/` | Normalize robust scores, preserve raw evidence and expose readiness/training verification. |
| `backend/demo/views.py`, serializers and URLs | Return accurate overview state and scoped readiness data. |
| `frontend/src/` | Render normalized scores, separated fault state and data-readiness progress. |
| Docker/workload tooling | Run bounded real CRUD/dependency/queue traffic for continuous completed windows. |
| `docs/` | Document collection duration, gates, recovery and reproducible model verification. |

## Open questions

None. The approved plan keeps five-minute windows, a 50-row Isolation Forest minimum, twelve-window sequences and a 60-sequence LSTM minimum; it increases honest data collection instead of weakening those gates.
