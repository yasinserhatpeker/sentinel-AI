---
slug: research-system-design
title: Research, requirements analysis and system design
author: Yasin Serhat Peker
area: platform
status: active
created: 2026-10-11 17:05
updated: 2026-10-11 17:05
---

# Phase 1 — design delivery

- [x] Extracted the 15 October milestone from the project report.
- [x] Researched observability signals, semantic conventions and incident management.
- [x] Recorded primary sources and converted findings into SentinelAI decisions.
- [x] Defined scope, non-goals and the first demo flow.
- [x] Defined the telemetry envelope, dimensions and minimum metric set.
- [x] Defined architecture components and synchronous/asynchronous boundaries.
- [x] Defined anomaly, incident and AI-analysis result boundaries.
- [x] Defined fault-injection scenarios and evaluation metrics.
- [x] Defined safeguards that keep fault injection in demo/test environments.
- [x] Recorded implementation risks and decisions for the 29 October milestone.

# Phase 2 — verification

Documentation verification was completed on 11 October 2026 by reviewing the project
report, research sources and resulting requirements/design documents. This milestone
does not produce production code, so no implementation command is required.

# Phase 3 — next milestone handoff

- [ ] Build the demo environment with Django REST API, PostgreSQL, Redis and Celery Worker.
- [ ] Instrument normal request, database, queue and worker flows with OpenTelemetry.
- [ ] Add fault injection and the `high_latency`, `error_burst`, `db_slowdown` and `queue_backlog` scenarios.
- [ ] Add data generation/processing commands that label normal and fault telemetry windows.
- [ ] Add an external benchmark pipeline for Exathlon, Alibaba Cluster Trace and LogHub.
- [ ] Normalize external benchmark inputs and report dataset-specific detection metrics.
- [ ] Add PostgreSQL telemetry/aggregate models and Celery aggregation jobs.
- [ ] Build the first Vue dashboard with system status and metric charts.
- [ ] Add contract tests and a reproducible local Docker demo.
