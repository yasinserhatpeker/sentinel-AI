---
slug: anomaly-detection-fault-experiments
title: Anomaly detection and fault injection experiments
author: Yasin Serhat Peker
area: ml
status: done
created: 2026-11-17 10:58
updated: 2026-11-17 16:31
---

# Tasks — Anomaly detection and fault injection experiments

## Phase 0 — Probe and gates

- [x] Read `AGENTS.md`, `specs/README.md`, templates and the completed telemetry-feature spec.
- [x] Inspect current feature models/materialization, Celery tasks, APIs, frontend contracts and demo-service fault surface.
- [x] Record all blocking decisions in `design.md`.
- [x] Record the eight implementation packages and verification baselines.
- [x] Receive explicit user approval and change all three files from `draft` to `active` (2026-11-17).

## Phase 1 — Implement

### Package 1 — Contract and data foundation

- [x] Add bounded feature data-quality reporting.
- [x] Define additive `features.v2` storage and fixed feature-name contract without modifying `features.v1`.
- [x] Materialize cyclic-time, 5/10/15-minute lag and 15/30/60-minute rolling fields from completed windows only.
- [x] Materialize static-graph upstream/downstream summaries and dependency deltas.
- [x] Add deterministic, idempotent and leakage-safe feature tests.

### Package 2 — Baseline detectors

- [x] Define the versioned detector interface and decision reason contract.
- [x] Implement configurable service-aware static thresholds.
- [x] Implement robust rolling Median/MAD detection with minimum-sample and zero-dispersion handling.
- [x] Persist retry-safe baseline decisions and add unit tests.

### Package 3 — Isolation Forest lifecycle

- [x] Add pinned, bounded ML/artifact dependencies to the backend image.
- [x] Implement time-ordered normal-data selection, preprocessing and minimum-sample gates.
- [x] Persist model metadata and a versioned local-volume artifact reference.
- [x] Implement activation and idempotent completed-window scoring with traceable decisions.
- [x] Add training, artifact, scoring and compatibility tests.

### Package 4 — Controlled faults and ground truth

- [x] Add experiment lifecycle, actor audit, bounded parameters and conflict rules.
- [x] Add signed local-only demo-service controls for high latency, error burst, database slowdown and queue backlog.
- [x] Add watchdog expiry, idempotent stop/recovery and worker-restart recovery.
- [x] Materialize `normal`, `fault_active` and `recovering` ground-truth windows.
- [x] Add authorization, bounds, repeatability and recovery integration tests.

### Package 5 — Evaluation and sequence research

- [x] Match detector decisions to ground-truth windows without future leakage.
- [x] Calculate confusion counts, precision, recall, F1, false-positive rate, detection delay and recovery delay.
- [x] Generate deterministic 12-window LSTM journals with time-ordered train/validation/test splits.
- [x] Add an offline LSTM prototype behind minimum-data and explicit-run gates; never auto-activate it.
- [x] Add metric, sequence and comparison tests.

### Package 6 — Application APIs

- [x] Add scoped anomaly list/detail APIs.
- [x] Add model list/train/activate APIs with super-admin authorization.
- [x] Add fault experiment create/list/stop/repeat APIs with local-only denial rules; list records carry the bounded detail contract.
- [x] Add evaluation APIs and compatible System Overview anomaly enrichment.
- [x] Add serializer, authorization, scope and stable-error tests.

### Package 7 — Operator UI

- [x] Add authenticated top navigation for overview, Service Health, anomalies, fault experiments and model evaluation.
- [x] Add overview anomaly/fault cards and dependency status treatment.
- [x] Add anomaly list/detail and fault/ground-truth annotations to metric trends.
- [x] Add super-admin fault controls/history with explicit active-fault warnings.
- [x] Add detector/model comparison views and loading/empty/partial/error states.
- [x] Add frontend state/component tests and preserve the existing corporate green design.

### Package 8 — Verification and closeout

- [x] Run the full backend, frontend, Compose and whitespace suites.
- [x] Execute repeatable normal/high-latency/error/database/queue experiments and record evidence.
- [x] Record per-detector metrics and explain dataset/sample limitations.
- [x] Document feature schema, model lifecycle, fault safety, experiment reproduction and UI operation.
- [x] Complete every acceptance criterion, archive gate and commit trailer check.

## Phase 2 — Verification record

| Criterion | Tag | Evidence |
|---|---|---|
| Feature v2 determinism, null semantics, dependency/time/lag/rolling fields | `auto:test` | Passed in the 51-test backend suite, 2026-11-17. |
| Baseline, Isolation Forest, fault, ground-truth, evaluation and sequence behaviour | `auto:test` | Passed in the 51-test backend suite; 3/3 shared fault tests also passed, 2026-11-17. |
| API authentication, scope and denial behaviour | `auto:test` | Passed in the 51-test backend suite, 2026-11-17. |
| Frontend states and production bundle | `auto:build` | Passed: 4/4 Vitest tests and Vite production build, 2026-11-17. |
| Compose validity | `auto:check` | Passed: `docker compose config --quiet`, 2026-11-17. |
| Formatting and patch integrity | `auto:check` | Passed: `git diff --check`, 2026-11-17. |
| End-to-end controlled experiment and UI | `manual:ui` | Passed: four real local fault runs, completed-window feature/scoring/evaluation finalization and visible UI evaluation output, 2026-11-17. |

### Incremental verification — Packages 1 and 2

- `docker compose run --rm --build api python manage.py test demo.tests.test_feature_pipeline` — passed, 7 tests, 2026-11-17.
- `docker compose run --rm --build api python manage.py test demo.tests.test_feature_pipeline demo.tests.test_baseline_detectors` — passed, 12 tests, 2026-11-17.
- `docker compose run --rm api python manage.py test demo.tests` — passed baseline after Package 1, 30 tests, 2026-11-17.
- `docker compose run --rm api python manage.py test demo.tests` — passed after Package 2, 35 tests, 2026-11-17.
- `docker compose run --rm --build api python manage.py test demo.tests.test_isolation_forest demo.tests.test_baseline_detectors demo.tests.test_feature_pipeline` — passed, 15 tests, 2026-11-17.
- `docker compose run --rm api python manage.py test demo.tests` — passed after Package 3, 38 tests, 2026-11-17.
- `PYTHONPATH=demo-services python3 -m unittest common.test_fault` — passed, 3 tests, 2026-11-17.
- `docker compose run --rm --build api python manage.py test demo.tests.test_fault_experiments demo.tests.test_isolation_forest demo.tests.test_baseline_detectors demo.tests.test_feature_pipeline` — passed, 21 tests, 2026-11-17.
- `docker compose run --rm api python manage.py test demo.tests` — passed after Package 4, 44 tests, 2026-11-17.
- Real Compose signed-control handshake on `payments-api` — start/status/stop/idle passed; a bounded 250 ms latency fault produced a measured 298.9 ms business request and was explicitly cleared, 2026-11-17.
- `docker compose run --rm --build api python manage.py test demo.tests.test_evaluation_sequences demo.tests.test_fault_experiments demo.tests.test_isolation_forest` — passed, 12 tests, 2026-11-17.
- `docker compose run --rm api python manage.py test demo.tests` — passed after Package 5, 47 tests, 2026-11-17.
- `docker compose run --rm --build api python manage.py test demo.tests.test_analysis_api demo.tests.test_system_overview demo.tests.test_evaluation_sequences` — passed, 10 tests, 2026-11-17.
- `docker compose run --rm api python manage.py test demo.tests` — passed after Package 6, 51 tests, 2026-11-17.
- `docker compose run --rm frontend npm test -- --run` — passed after Package 7, 4 tests across 2 files, 2026-11-17.
- `docker compose run --rm frontend npm run build` — passed after Package 7; Vue type-check and Vite production build completed, 22 modules transformed, 2026-11-17.
- Manual UI verification — authenticated System Overview, Service Health, Anomalies, Fault experiments and Model evaluation screens rendered in the corporate green design; responsive navigation and top-of-view reset verified at the in-app browser viewport, 2026-11-17.
- `docker compose exec -T api python manage.py verify_fault_experiments --duration 15 --queue-jobs 30` — passed; high latency 102.6→513.8 ms, error burst 200→503, database slowdown 99.2→528.1 ms, queue depth 0→10 and queued records 0→30; every run stopped and produced 6 ground-truth windows, 2026-11-17.
- `docker compose exec -T api python manage.py finalize_fault_evaluations --lookback-minutes 30` — passed; 82 aggregate rows, 8 `features.v2` rows, 16 detector decisions and persisted evaluation results produced, 2026-11-17.
- Evaluation limitation — static threshold detected the first latency/error/database smoke windows with precision/recall/F1 1.0 and zero delay; repeated same-window experiments exposed FPR 0.5; Median/MAD lacked sufficient history, queue fault did not cross the completed feature threshold, 12-window sequences remained gated and Isolation Forest remained below its 50-normal-sample training gate.
- `docker compose config --quiet` — passed, 2026-11-17.
- `git diff --check` — passed, 2026-11-17.
- Model-state note: local/disposable Docker startup and test containers generate the required uncommitted migration state; no migration file is added to source.

- [x] Record every automatic command result.
- [x] Confirm the future commit trailer uses `Spec: anomaly-detection-fault-experiments`.
