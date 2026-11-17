---
slug: anomaly-detection-fault-experiments
title: Anomaly detection and fault injection experiments
author: Yasin Serhat Peker
area: ml
status: done
created: 2026-11-17 10:58
updated: 2026-11-17 16:31
---

# Design — Anomaly detection and fault injection experiments

## Approach

The implementation is divided into eight ordered packages. Package 1 establishes data quality and the immutable `features.v2` contract. Packages 2 and 3 add comparable baseline and Isolation Forest detectors behind one interface. Package 4 creates bounded fault experiments and ground truth. Package 5 evaluates detectors and prepares time-ordered LSTM sequences. Package 6 exposes scoped APIs. Package 7 adds the operator UI. Package 8 verifies, documents and archives the work.

The active detector never consumes raw events directly. Completed minute aggregates materialize five-minute `features.v2` rows. A static dependency graph enriches each service row with upstream/downstream summaries. Lag and rolling calculations use only earlier completed windows, preventing future-data leakage. Every decision stores the detector/model/configuration and source feature identity required for replay.

## Blocking decisions

### Data ownership and retention

- Status: `confirmed`
- Scope, source and retention/deletion behaviour: existing raw telemetry remains local and retains 30 days. `features.v1` remains unchanged. Aggregate-only `features.v2`, model metadata, detector decisions, synthetic experiment ground truth and evaluation results remain in the local database until an explicit Docker-volume reset. Binary model artifacts live in a dedicated local Docker volume, are referenced by version and are never committed. LSTM sequence journals are derived, bounded and reproducible from feature rows.
- Migration required: yes; model-state changes are documented here. Per repository policy, agents do not generate or commit migration files; local Docker environments generate/apply their own migrations.

### Authentication and query visibility

- Status: `confirmed`
- Access mode and scope: anomaly/model/evaluation reads require the existing super-admin JWT and explicit `environment=local` plus bounded service/time filters where applicable. Fault experiment create/stop/repeat operations require an active super-admin and force `local`; machine telemetry credentials cannot control experiments.
- Denial behaviour: missing scope returns stable validation errors; unauthenticated requests return 401; authenticated non-super-admins and unsafe/non-local mutations return 403; unknown resources return 404 without leaking unrelated scope.

### Mutation, audit and logging

- Status: `confirmed`
- State-changing paths: model training/activation, detector scoring, experiment create/start/stop/repeat/recovery, ground-truth generation and evaluation materialization. Scoring is idempotent on detector/model/feature/config identity. Only one conflicting fault may run per target service.
- Audit and safe logging decision: persistent records capture actor ID, experiment/model/detector version, bounded parameters, timestamps and status transitions. Logs contain IDs, service, fault type, counts and status only; no passwords, tokens, raw request bodies or personal data.

### Telemetry contract and privacy

- Status: `confirmed`
- Schema/version and cardinality controls: `features.v2` preserves the fixed base numeric columns and stores derived context under a fixed nullable numeric-key allowlist in `feature_values`; arbitrary keys are prohibited. A static allowlisted dependency graph, cyclic time fields, three lag windows and 15/30/60-minute rolling summaries are computed from completed windows only. Detection/evaluation contracts are versioned and contain aggregate values, IDs and bounded reason codes; arbitrary dimensions and labels are prohibited.
- Redaction and external-egress decision: all training, scoring, experiments and evaluation remain local. No telemetry or model context leaves the machine in this milestone. External LLM and benchmark ingestion remain out of scope.

### Operational safety

- Status: `confirmed`
- Retry/idempotency, fault-injection controls and rollback: experiments are restricted to the `local` environment, allowlisted demo services and four allowlisted fault types. Configuration enforces maximum duration, latency, error probability and workload. A watchdog restores normal behaviour at expiry or worker restart. Stop/recovery operations are idempotent, conflicting runs are rejected and every fault parameter uses a reproducible random seed. Static/statistical/ML scoring can be disabled independently without affecting telemetry ingestion.

## Probe findings

- `backend/demo/models.py` — `TelemetryFeature` stores nullable aggregate-only `features.v1` rows keyed by schema/window/environment/service; no detector, model, experiment or evaluation models exist.
- `backend/demo/telemetry_ingestion.py` — five-minute materialization is retry-safe but contains only current-window service metrics; dependency, lag, rolling and cyclic-time fields are absent.
- `backend/demo/tasks.py` — Celery Beat already schedules minute aggregation, five-minute feature materialization and retention; it provides a natural place for completed-window scoring.
- `backend/demo/views.py` — authenticated, explicitly scoped aggregate and overview APIs exist; fault and anomaly endpoints do not.
- `backend/requirements.txt` — scikit-learn and model-artifact dependencies are not installed.
- `frontend/src/App.vue` — Service Health and System Overview are a single authenticated view; overview fields intentionally expose no incidents/anomaly score yet.
- `demo-services/` — real HTTP/ORM/queue telemetry is emitted, but no signed allowlisted fault-control contract exists.

## Rejected alternatives

| Option | Why not |
|---|---|
| Train directly from raw telemetry events | Raw events are high volume, irregular and can leak request-level dimensions; completed feature windows are reproducible and bounded. |
| Replace `features.v1` in place | It would break existing backfills and erase the contract used by the current dashboard milestone. |
| Random row-level train/test split | Adjacent windows are correlated and would leak future behaviour into training. Time-ordered splits are required. |
| Use only fixed thresholds | Thresholds provide an explainable baseline but cannot model multivariate dependency behaviour. |
| Make LSTM the first active detector | The local project does not yet have enough continuous labelled sequences; sequence generation and an offline prototype are safer and measurable. |
| Expose generic fault scripting | Arbitrary commands or payload mutation would violate the local operational-safety boundary. |
| Let an LLM decide anomalies | External egress is out of scope and advisory language models cannot replace traceable numeric detectors. |

## API and data contract

- Endpoint families:
  - `GET /api/anomalies/v1/` and `GET /api/anomalies/v1/<id>/`
  - `GET /api/models/v1/` and super-admin `POST /api/models/v1/train/`, `POST /api/models/v1/<id>/activate/`
  - `GET/POST /api/fault-experiments/v1/`, `POST /api/fault-experiments/v1/<id>/stop/`, `POST /api/fault-experiments/v1/<id>/repeat/`
  - `GET /api/evaluations/v1/`
  - existing `GET /api/telemetry/v1/overview/` evolves compatibly to `overview.v2` when anomaly fields are available.
- Feature contract: `features.v2`, one nullable aggregate-only row per completed five-minute `environment/service/window`; base metrics plus fixed cyclic-time, lag, rolling and dependency fields.
- Detector contract: `fit(dataset, configuration)`, `score(feature_row)`, `detect(score, configuration)`, `metadata()` with stable detector/version/reason codes.
- Decision contract: environment, service, feature row, detector type/version, model version when applicable, score, threshold, decision, severity, bounded feature contributions/reasons and timestamps.
- Experiment contract: UUID, local environment, allowlisted target/fault type, validated parameters, seed, actor, lifecycle timestamps/status and expected effects.
- Ground-truth contract: experiment, service, five-minute window, label (`normal`, `fault_active`, `recovering`) and fault severity.
- Evaluation contract: bounded experiment/time range, detector/version, confusion counts, precision, recall, F1, false-positive rate, detection delay and recovery delay.
- Compatibility: existing telemetry APIs, `overview.v1` consumers and `features.v1` remain valid during rollout. New UI types are additive.

## Eight implementation packages

1. **Contract and data foundation:** data-quality report, `features.v2`, dependency graph, cyclic time, lag/rolling materialization and sequence-safe splitting.
2. **Baseline detectors:** shared detector protocol, configurable static thresholds and robust Median/MAD statistical baseline.
3. **Isolation Forest lifecycle:** scikit-learn dependency, training/metadata/artifact storage, activation and idempotent completed-window scoring.
4. **Controlled faults and ground truth:** signed local control, four bounded fault types, experiment lifecycle/watchdog/recovery and labelled windows.
5. **Evaluation and sequence research:** confusion metrics, delay metrics, detector comparison, LSTM-ready 12-window journals and an offline gated prototype.
6. **Application APIs:** scoped anomaly/model/fault/evaluation serializers, endpoints, authorization and compatible overview enrichment.
7. **Operator UI:** top navigation, overview cards, annotated service trends, anomaly list/detail, experiment controls/history and evaluation/model views.
8. **Verification and closeout:** unit/integration/UI checks, reproducible experiment evidence, documentation, spec verification and archive gate.

## Impact analysis

- Changed: local data models/contracts, feature tasks, ML dependencies, demo fault behaviour, API surface and authenticated UI navigation.
- Possibly affected: Celery scheduling/load, Docker image size, local database growth, Service Health query latency and demo-service recovery.
- Risk: false confidence from insufficient normal data, data leakage, unsafe persistent faults, duplicate scoring, model artifact drift and misleading null handling.
- Recommendation: deliver packages in order, keep all faults local and bounded, preserve null semantics, require minimum-sample gates, compare every ML result with baselines and do not activate LSTM automatically.

## Decision log

| Date | Decision | Why |
|---|---|---|
| 2026-11-17 | Preserve `features.v1` and introduce `features.v2`. | Existing telemetry and dashboard behaviour remain compatible. |
| 2026-11-17 | Include dependency, cyclic-time, lag and rolling features. | The supervisor requested service-dependency and temporal context. |
| 2026-11-17 | Compare static threshold, robust statistical and Isolation Forest detectors. | Baselines are required to demonstrate ML value objectively. |
| 2026-11-17 | Produce LSTM-ready sequences and only an offline gated prototype. | Sequence learning needs substantially more continuous data than the current local dataset guarantees. |
| 2026-11-17 | Restrict faults to allowlisted local demo scenarios. | Controlled experiments must not become a general-purpose disruption interface. |
| 2026-11-17 | User approved the spec and all confirmed implementation gates. | Implementation may begin under the eight ordered packages. |
| 2026-11-17 | Store derived `features.v2` context in one fixed-key JSON field while preserving base columns. | Lag and rolling expansion would otherwise add hundreds of sparse columns; the allowlist keeps cardinality fixed and null semantics explicit. |

## Rules consulted

- `AGENTS.md`
- `specs/README.md`
- `specs/_template/requirements.md`
- `specs/_template/design.md`
- `specs/_template/tasks.md`
- `specs/archive/2026-10-27-telemetry-retention-features/`
