---
slug: anomaly-hardening-real-data-readiness
title: Anomaly hardening and real-data model readiness
author: Yasin Serhat Peker
area: ml
status: active
created: 2026-11-17 16:52
updated: 2026-11-17 23:30
---

# Design — Anomaly hardening and real-data model readiness

## Approach

Work proceeds in three ordered packages. Package 1 hardens runtime correctness: fault state moves from container-local files to bounded Redis keys whose TTL is derived from experiment expiry, robust detector output is split into retained raw evidence and a finite normalized score, and overview fault semantics are corrected. Package 2 establishes honest data readiness: a bounded workload container invokes real business/dependency/queue flows without inserting telemetry directly, while scoped readiness reports measure completed-window continuity and model gates during the continuous collection run. Package 3 completes model verification: real windows train and activate Isolation Forest, chronological journals train the offline LSTM prototype, the operator UI exposes readiness/results, and the full automated/manual regression closes the spec.

## Blocking decisions

### Data ownership and retention

- Status: `confirmed`
- Scope, source and retention/deletion behaviour: Redis holds only bounded local fault-control state until explicit stop or TTL expiry. Workload output consists of ordinary local demo business records and the existing telemetry/aggregate/feature records governed by current retention. Readiness rows are derived summaries. Model artifacts and sequence journals retain the existing local-volume/database lifecycle.
- Migration required: possible for additive detector score/readiness state; any requirement is documented but no migration file is generated or committed by the agent.

### Authentication and query visibility

- Status: `confirmed`
- Access mode and scope: fault mutation, readiness and model lifecycle remain existing super-admin-only operations with explicit `environment=local`, service and bounded time scope. Internal service controls remain HMAC signed and unavailable through public business endpoints.
- Denial behaviour: unauthenticated requests return 401, non-super-admins or non-local mutation return 403, malformed/missing scope returns stable 400 errors and unknown scoped resources return 404.

### Mutation, audit and logging

- Status: `confirmed`
- State-changing paths: fault start/stop/expiry/reconciliation, workload business mutations, model train/activate/score and sequence materialization. Operations remain idempotent or carry deterministic identifiers; only one conflicting service fault may be active.
- Audit and safe logging decision: database experiment/model records remain the audit trail. Redis values contain only experiment ID, allowlisted service/type/parameters, seed and UTC lifecycle timestamps. Logs contain bounded IDs, counts and status only; no JWT, HMAC secret, password, request body or personal data.

### Telemetry contract and privacy

- Status: `confirmed`
- Schema/version and cardinality controls: the workload emits no metric payload and writes no telemetry table; existing instrumentation observes real HTTP/ORM/queue/runtime work. Detector output adds fixed finite score semantics while keeping model/configuration/feature evidence. Readiness uses aggregate counts and fixed reason codes only.
- Redaction and external-egress decision: all traffic, storage, artifacts, training and evaluation stay in the local Docker topology. No external egress is introduced.

### Operational safety

- Status: `confirmed`
- Retry/idempotency, fault-injection controls and rollback: Redis keys are service scoped, signed, allowlisted and TTL bounded. Missing/invalid/expired Redis state means normal behaviour. Explicit stop deletes state idempotently; watchdog reconciles database state. Workload rate, duration and concurrency are bounded and stoppable. The previous implementation remains recoverable by stopping experiments and disabling the workload profile.

## Probe findings

- `demo-services/common/fault.py` — runtime fault effects are currently backed by a container-local file, so `docker compose restart` preserves stale state.
- `backend/demo/detection/baseline.py` — robust z-score divides by a near-zero fallback scale when median absolute deviation is zero, producing extremely large values.
- `backend/demo/views.py` — overview derives a latest fault subtitle independently from the active fault count.
- `backend/demo/detection/isolation_forest.py` — training correctly requires at least 50 time-ordered feature rows.
- `backend/demo/detection/sequences.py` — twelve-window journals are contiguous and the offline prototype correctly requires at least 60 journals.
- Five-minute feature windows require approximately 250 minutes for 50 fresh rows and approximately 355 minutes for 60 twelve-window journals from 71 contiguous feature rows; services can collect concurrently.
- A lost reporting task left one database row in `queued` state while the Redis broker queue was empty. The stale row made `queue.oldest_message_age` increase indefinitely, and Median/MAD then marked every new reporting window anomalous.
- Isolation Forest readiness and training excluded rows predicted anomalous by baseline detectors. This incorrectly treated a comparator's prediction as ground truth and allowed a false positive to starve the independent model's training set.

## Rejected alternatives

| Option | Why not |
|---|---|
| Clear `/tmp` only at container startup | A restart can still race with database state and local files remain an unshared, weakly expiring source of truth. |
| Lower Isolation Forest or LSTM sample gates | It would make the UI green without proving the requested real-data behaviour. |
| Backdate or insert telemetry/features directly | It violates the real-observation requirement and invalidates temporal evaluation. |
| Generate many requests in one minute to replace elapsed time | It increases volume, not independent completed windows or sequence continuity. |
| Hide or cap only the UI score | Persisted decisions and API comparisons would remain numerically misleading. |
| Delete false-positive decisions or rewrite historical telemetry | It would destroy traceability and conceal the source defect instead of correcting queue semantics and training eligibility. |

## API and data contract

- Internal fault state: versioned Redis JSON at a fixed service-scoped key, bounded allowlisted fields and TTL no longer than the experiment expiry.
- Detector decision: retain technical `raw_score`; expose finite `normalized_score` in `[0, 1]`, threshold/severity and bounded reasons/evidence.
- Overview: separate `active_fault_count`, `active_faults`, `recovering_faults` and nullable `latest_completed_fault` semantics.
- Readiness: explicit environment/service/time scope; feature sample/continuity/gap/missingness counts, journal split counts, gate minimums, readiness booleans and stable reason codes.
- Isolation Forest training eligibility: baseline decisions remain independent evaluation evidence. Only windows labelled `fault_active` or `recovering` by controlled-experiment ground truth are excluded from normal training.
- Reporting queue age: a zero broker depth means no queued message and therefore zero oldest-message age, even if an orphaned business row remains after local broker loss. Unknown broker state retains the bounded database observation rather than inventing zero.
- Workload: bounded environment configuration for duration, interval/concurrency, deterministic seed and base service URLs; business endpoints only.
- Compatibility: existing public telemetry, feature and business contracts remain additive and valid.

## Impact analysis

- Changed: local fault runtime state, robust score representation, overview semantics, Docker topology, workload automation and model-readiness UI/API.
- Possibly affected: Redis load, local business-row volume, Celery queue volume, detector decision consumers and dashboard types.
- Risk: Redis outage, workload overproduction, incomplete temporal windows, stale model artifacts and misleading readiness caused by gaps.
- Recommendation: implement and verify lifecycle hardening first, then score/overview fixes, then bounded collection; do not start training until readiness reports no blocking gap.

## Decision log

| Date | Decision | Why |
|---|---|---|
| 2026-11-17 | Make every manual-test row successful, including real Isolation Forest and LSTM gates. | The requester explicitly expanded completion beyond defect repair. |
| 2026-11-17 | Preserve five-minute/50-row/60-sequence gates and collect real elapsed-time data. | Safety and temporal validity take priority over a faster artificial green result. |
| 2026-11-17 | Use Redis TTL state for local fault effects. | It provides shared expiry semantics and removes container-local stale state. |
| 2026-11-17 | User approved the spec and all confirmed gates. | Implementation may proceed through the ordered packages. |
| 2026-11-17 | Consolidate delivery into three packages without reducing scope. | The requester wants three reviewable packages: reliability, real-data readiness and model completion. |
| 2026-11-17 | Keep baseline predictions independent from Isolation Forest training eligibility and derive exclusions from controlled ground truth. | Reporting false positives demonstrated that one detector must not define another detector's training truth. |
| 2026-11-17 | Bind oldest-message age to actual broker depth. | A stale database status is not a queued broker message and must not create an unbounded queue-age signal. |

## Rules consulted

- `AGENTS.md`
- `specs/README.md`
- `backend/.ai/backend-conventions.md`
- `backend/.ai/testing.md`
- `backend/.ai/drf-viewsets.md`
- `backend/.ai/queryset-authorization.md`
- `backend/.ai/basemodel-audit.md`
- `specs/archive/2026-11-17-anomaly-detection-fault-experiments/`
