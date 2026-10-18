---
slug: demo-telemetry-foundation
title: Demo telemetry foundation
author: Yasin Serhat Peker
area: platform
status: active
created: 2026-10-18 16:11
updated: 2026-10-18 16:25
---

# Design — Demo telemetry foundation

## Approach

Use a monorepo with `backend/`, `frontend/`, `telemetry/`, `specs/` and root local-runtime
configuration. Add a shared package only if concrete reuse appears. Run a small local
system through Docker Compose:
Django REST API, PostgreSQL, Redis, Celery Worker and OpenTelemetry Collector. A normal
token-protected order operation will persist a demo order, interact with Redis and
schedule a report task so one request creates correlated HTTP, database, cache/queue and
worker telemetry.

The Collector is the telemetry boundary for this spec. It receives signals but does not
yet send them to SentinelAI ingestion storage; that contract belongs to the next spec.

## Blocking decisions

### Data ownership and retention

- Status: `confirmed`
- Scope, source and retention/deletion behaviour: local synthetic demo data only; resettable Docker volumes; no customer or production telemetry.
- Migration required: yes, additive and reversible; no data migration. It is reported
  here and generated per local Docker environment outside the source tree.

### Authentication and query visibility

- Status: `confirmed`
- Access mode and scope: static demo token from local environment configuration; local Docker only.
- Denial behaviour: missing or invalid token receives a stable denial response; malformed telemetry and out-of-scope requests will fail closed when ingestion is added in the next spec.

### Mutation, audit and logging

- Status: `not_applicable: the first local demo has no incident-state mutation or audit surface`
- State-changing paths: demo record creation and background job scheduling only.
- Audit and safe logging decision: logs contain correlation IDs and bounded metadata only.

### Telemetry contract and privacy

- Status: `confirmed`
- Schema/version and cardinality controls: use the documented common context fields; route templates rather than raw paths; no user identifiers in metric dimensions.
- Redaction and external-egress decision: local synthetic telemetry only; no LLM or external provider egress.

### Operational safety

- Status: `confirmed`
- Retry/idempotency, fault-injection controls and rollback: Celery tasks are retry-safe and idempotent where practical; fault injection is out of scope; `docker compose down -v` resets the local demo.

## Probe findings

- `docs/MILESTONES.md` — the 29 October deliverable is telemetry infrastructure, demo system and dashboard foundation; anomaly detection belongs to 12 November.
- `docs/demo-services-and-data-collection.md` — the agreed demo topology is Django, PostgreSQL, Redis, Celery, Vue and an OpenTelemetry Collector.
- `AGENTS.md` — backend, frontend and telemetry boundaries belong in one monorepo; shared packages are optional.
- `backend/.ai/backend-conventions.md` — ingestion validation, normalization, persistence and asynchronous processing must remain separate.

## Rejected alternatives

| Option | Why not |
|---|---|
| Several independent business microservices | Adds operational complexity without improving the first telemetry proof. |
| Fault injection in this spec | The project report schedules controlled fault experiments for the 12 November milestone. |
| Sending telemetry directly to an LLM | LLM analysis is not part of the telemetry critical path and is out of this milestone. |

## API and data contract

- Endpoint(s): token-protected order creation and report-job operations; exact route names remain implementation details.
- Event/schema fields: OpenTelemetry service and trace context plus documented metric dimensions.
- Query parameters and response shape: local demo API only; SentinelAI ingestion/query contract is deferred.
- Compatibility: no pre-existing implementation to preserve.

## Impact analysis

- Changed: local runtime topology and telemetry-producing demo components.
- Possibly affected: next ingestion, aggregation and dashboard specs consume the emitted signal names.
- Risk: unbounded metric cardinality or accidental sensitive logging.
- Recommendation: approve the two open decisions, then implement the smallest normal flow first.

## Decision log

| Date | Decision | Why |
|---|---|---|
| 2026-10-18 | Keep this spec limited to telemetry production and Collector intake | It creates a stable base for ingestion and dashboard specs without mixing later ML work. |
| 2026-10-18 | Use monorepo boundaries, demo-token auth, orders and report jobs | Explicit user decisions for the first runnable demo. |
| 2026-10-18 | Generate development migrations in a named Docker volume | Preserves the project rule that agents do not commit generated migration files. |

## Rules consulted

- `AGENTS.md`
- `specs/README.md`
- `backend/.ai/backend-conventions.md`
- `backend/.ai/testing.md`
