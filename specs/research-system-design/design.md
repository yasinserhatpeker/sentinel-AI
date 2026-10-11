---
slug: research-system-design
title: Research, requirements analysis and system design
author: Yasin Serhat Peker
area: platform
status: active
created: 2026-10-11 17:05
updated: 2026-10-11 17:05
---

# Gates

- Model ownership: not_applicable: no persistent domain model is implemented in this milestone.
- Authentication: not_applicable: no HTTP endpoint is implemented in this milestone.
- Permission & row visibility: not_applicable: no query surface is implemented in this milestone.
- Mutation, audit & logging: not_applicable: design-only milestone; event audit is specified below.
- Client data protection boundary: confirmed: sensitive telemetry is redacted before persistence and LLM context creation.

# Approach

Use OpenTelemetry-compatible events as the ingestion boundary. Django REST validates and
normalizes inbound telemetry, PostgreSQL stores queryable aggregates and incident state,
Redis/Celery handles asynchronous aggregation and detection, and Vue presents the
operator-facing dashboard. The detector emits evidence-linked anomaly records; a later
correlation service groups records by time, service, deployment and dependency context.

LLM analysis is deliberately downstream of deterministic detection and correlation. It
receives redacted, bounded context and returns structured hypotheses, evidence references,
confidence and suggested next checks. It does not mutate infrastructure.

# Probe findings

- The report names HTTP latency/request rate/error rate, CPU/RAM, database connections and
  queue data as the minimum demo set; the design adds deployment metadata for correlation.
- OpenTelemetry is the common collection vocabulary, while PostgreSQL remains the system
  of record for normalized telemetry and analysis results.
- Redis/Celery is required for periodic aggregation and future analysis jobs, so ingestion
  remains responsive and does not call an LLM inline.
- The project uses a lightweight spec workflow and task-specific AI rules; domain behavior is defined only by SentinelAI requirements.

# Data flow

```text
Demo services / OTEL collector
        -> telemetry ingestion API
        -> validation + normalization
        -> PostgreSQL raw/aggregate records
        -> Celery aggregation + detector
        -> anomaly records
        -> incident correlation
        -> redacted context builder -> LLM analysis
        -> Vue dashboard and investigation timeline
```

# Minimum telemetry model

Every event carries `schema_version`, `event_id`, `timestamp`, `environment`, `service`,
`instance`, `deployment_id` and optional `trace_id`. Values are numeric or bounded enums;
payloads are size-limited and raw message fields are redacted before persistence.

| Signal | Required measurements | Initial aggregation |
|---|---|---|
| HTTP | request count, latency p50/p95/p99, 4xx/5xx count, error rate | 1-minute service/route buckets |
| Runtime | CPU utilization, memory utilization, process restarts | 1-minute service/instance buckets |
| Database | connection usage, query latency, timeout/error count | 1-minute service/database buckets |
| Queue | queue depth, oldest-message age, enqueue/dequeue rate, failure count | 1-minute queue buckets |
| Deployment | deployment id, version, start/end time, changed services | event-based dimension |

# Fault-injection scenarios

| Scenario | Controlled injection | Expected evidence | Success measure |
|---|---|---|---|
| High latency | add 300–800 ms delay to one demo route for 5 minutes | p95/p99 rise, trace duration rise, route-local impact | detection delay and recall |
| Error burst | return 5xx for 10–20% of requests on one route | error-rate spike, matching request count, affected deployment | precision and false-positive rate |
| Database slowdown | add bounded query delay or reduce demo pool capacity | DB latency/timeout rise followed by request latency | incident lead time and correlation quality |
| Queue backlog | pause one consumer or cap processing rate | depth and oldest-age growth, downstream lag | backlog detection delay and recovery visibility |

Fault injection is enabled only by an explicit demo/test flag, records a scenario id and
start/end time, and is never enabled by default.

# Decision log

| Date | Decision | Reason |
|---|---|---|
| 2026-10-11 | Keep detection deterministic before LLM analysis | measurable behavior, reproducible demos and safer failure modes |

# Rejected alternatives

| Alternative | Rejection reason |
|---|---|
| Call the LLM directly from ingestion | adds latency, cost and nondeterminism to the critical path |
| Store only pre-aggregated metrics | loses evidence needed for incident investigation and evaluation |
