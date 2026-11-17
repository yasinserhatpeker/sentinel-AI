---
slug: anomaly-detection-fault-experiments
title: Anomaly detection and fault injection experiments
author: Yasin Serhat Peker
area: ml
status: done
verification: full
created: 2026-11-17 10:58
updated: 2026-11-17 16:31
branches: core-development
---

# Anomaly detection and fault injection experiments

## Problem

SentinelAI materializes real five-minute service features but cannot yet distinguish normal behaviour from anomalies, generate repeatable fault ground truth, compare detectors, or explain detection quality in the dashboard. The current `features.v1` contract also lacks service-dependency and temporal context required to evaluate correlated and sequence-aware behaviour.

## Scope

**In:** `features.v2` with fixed base, dependency, cyclic-time, lag and rolling fields; data-quality reporting; configurable static-threshold and robust statistical baselines; versioned Isolation Forest training/scoring; bounded local fault experiments for high latency, error burst, database slowdown and queue backlog; labelled ground truth and recovery windows; precision, recall, F1, false-positive rate, detection delay and recovery delay; LSTM-ready sequence journals and an offline prototype; scoped anomaly/fault/evaluation APIs; authenticated Turkish operator UI with English technical terms; automated backend/frontend/integration verification.

**Out:** production fault injection, automatic remediation, alert delivery, external LLM calls, unbounded model tuning, a production LSTM detector, external benchmark-dataset ingestion and cross-environment model sharing.

**Existing behaviour preserved:** `telemetry.v1`, minute aggregates, `features.v1`, the existing Service Health dashboard, JWT/CSRF authentication, 30-day raw-event retention and real demo-service CRUD/workload flows remain compatible.

## Acceptance criteria

- [x] `features.v2` is deterministic, idempotent and scoped by environment/service/window; it preserves missing observations as null and adds fixed dependency/time/lag/rolling fields without altering `features.v1`. → `auto:test`
- [x] A bounded data-quality report exposes sample counts, missingness, duplicate windows and sequence gaps without raw payloads or high-cardinality dimensions. → `auto:test`
- [x] Static-threshold and robust statistical detectors implement one versioned detector contract and persist traceable decisions. → `auto:test`
- [x] Isolation Forest training persists model metadata and an artifact reference; retry-safe scoring records model version, feature schema, input feature row and decision configuration. → `auto:test`
- [x] High-latency, error-burst, database-slowdown and queue-backlog experiments are repeatable, local-only, super-admin controlled, bounded by duration/severity and automatically recover. → `auto:test`
- [x] Ground-truth windows label `normal`, `fault_active` and `recovering`; evaluation calculates precision, recall, F1, false-positive rate, detection delay and recovery delay for a bounded experiment range. → `auto:test`
- [x] Twelve-window LSTM-ready sequences are generated in time order without leakage; an offline prototype can train/evaluate when the minimum sample gate is met and is never selected as the active detector automatically. → `auto:test`
- [x] JWT-protected APIs require explicit environment, service and/or time scope; fault mutations reject non-super-admins, non-local environments, unknown services, unsafe parameters and conflicting runs. → `auto:test`
- [x] The Turkish UI provides navigation, anomaly overview/list/detail, fault experiment controls/history and detector evaluation while keeping technical terms in English and representing loading, empty, partial and error states. → `auto:build`
- [x] A controlled end-to-end run produces telemetry, `features.v2`, detector decisions, ground truth, evaluation results and visible UI output without fabricated metric values. → `manual:ui`
- [x] Backend tests, frontend tests/build, Docker Compose validation and whitespace checks pass. → `auto:check`

## Affected areas

| Area | Planned change |
|---|---|
| `backend/demo/models.py` | Versioned model metadata, detection, fault experiment, ground-truth and evaluation records; feature-v2 storage contract. |
| `backend/demo/telemetry_ingestion.py` | Deterministic dependency/time/lag/rolling materialization and data-quality probes. |
| `backend/demo/detection/` | Shared detector interface, baseline detectors, Isolation Forest lifecycle, evaluation and sequence generation. |
| `backend/demo/tasks.py` | Scheduled feature materialization/scoring, bounded experiment control, recovery and evaluation tasks. |
| `backend/demo/views.py`, serializers and URLs | Scoped anomaly, experiment, model and evaluation APIs. |
| `demo-services/` | Allowlisted, signed local fault controls and observable fault behaviour. |
| `frontend/src/` | Operator navigation, anomaly/fault/evaluation views and trend annotations. |
| `docs/` | Feature schema, experiment protocol, detector comparison and reproducibility guide. |
| CI/Docker | ML dependency installation and full local verification. |

## Open questions

None. The approved implementation may refine numeric defaults through documented configuration and experiments, but it may not weaken the local-only safety boundary or change the fixed contracts without updating this spec.
