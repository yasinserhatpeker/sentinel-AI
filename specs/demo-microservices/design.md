---
slug: demo-microservices
title: Local demo microservice topology
author: Yasin Serhat Peker
area: platform
status: active
created: 2026-10-27 10:25
updated: 2026-10-27 14:39
---

# Design — Local demo microservice topology

## Approach

SentinelAI will remain the control-plane application: its Django API ingests telemetry, stores
bounded raw events, aggregates minute data and exposes dashboard queries. A separate
`demo-services/` layer will contain five independently buildable Django REST applications. Each
service owns a Django project/app, models, serializers, views, URL configuration, local schema initialization,
Dockerfile, health endpoint, domain API and local PostgreSQL database. They share an OTLP
collector endpoint, but do not share process memory, runtime state, database, container image or
dashboard credentials.

```text
orders-api ───────┐
inventory-api ────┤── telemetry.v1 + HMAC signature ─> SentinelAI telemetry ingestion ──> PostgreSQL
payments-api ─────┤
reporting-worker ─┤── OTLP (inspection route) ───────> collector
notifications-api ┘
                                      │
                                      └──> Vue dashboard (aggregate reads only)
```

Each service emits the same versioned telemetry envelope with a unique `service.name`, generated
trace ID, deployment ID and instance ID. Its metric values are measured from real request
handling, ORM/database operations and background-task behaviour—not from hard-coded dashboard
profiles. A secret-derived HMAC signature authenticates the local telemetry publisher; OTLP remains an
independently inspectable Collector path because the stock Collector cannot transform OTLP to the
application's custom JSON envelope without a dedicated adapter. A normal workload exercises each
domain API; a service-local fault changes only that application's latency, error rate, database
behaviour or queue depth. Fault state is ephemeral and reset by a container restart.

## Blocking decisions

### Data ownership and retention

- Status: `confirmed`
- Scope and retention: generated local technical telemetry only; existing SentinelAI raw-event
  retention and aggregate behaviour apply. No new persistent application model is planned.
- Migration required: yes, for each service-owned domain model. Per project rules these are
  generated in the local Docker environment and are never committed to the repository.

### Service data ownership

- Status: `confirmed`
- Topology: each demo application has its own PostgreSQL database in the local Compose topology.
  There is no cross-service ORM import, shared model package or direct cross-service database
  query. SentinelAI stores only its telemetry events and aggregates.
- Domain ownership: `orders-api` owns orders, `inventory-api` owns stock, `payments-api` owns
  authorizations, `reporting-worker` owns report jobs and `notifications-api` owns notifications.
- Migration rule: every service owns and applies its own Django migrations in an isolated local
  volume; generated migration files are never committed by an agent. The SentinelAI control-plane
  API never generates another service's migration.

### Authentication and query visibility

- Status: `confirmed: dashboard users continue to use super-admin JWT access. Demo-service`
  ingestion uses an HMAC signature derived from the existing `DJANGO_SECRET_KEY`; the raw secret
  is never returned by an endpoint, rendered in Vue, logged or committed.
- Query visibility: dashboard requests remain explicitly scoped by local environment, selected
  service and bounded time range.
- Denial behaviour: missing or invalid machine signature rejects ingestion with a stable denial;
  untrusted browser callers cannot call the collector or demo service control interface.

### Mutation, audit and logging

- Status: `confirmed`
- State-changing paths: each demo service handles generated local domain work through its own
  view/serializer/model boundary; fault state is local to one running container and clears on
  restart. SentinelAI persists only validated telemetry.
- Audit and safe logging decision: log service name, bounded scenario ID and generated trace ID;
  never log credentials, request bodies, payment details or tokens.

### Telemetry contract and privacy

- Status: `confirmed`
- Schema: existing `telemetry.v1` envelope and metric names remain. Required context includes
  `environment=local`, `service`, `instance`, `deployment_id` and generated `trace_id`.
- Cardinality/redaction: service names are a fixed allowlist of five; no user identifiers,
  customer order contents, inventory identifiers or payment values enter telemetry.
- External-egress decision: none. All containers communicate only on the local Compose network.

### Operational safety

- Status: `confirmed: only docker compose exec <service> ... enables a named local scenario;`
  no host port is published for a fault-control endpoint. Scenarios expire automatically and
  container restart is the rollback path.
- Retry/idempotency: generated workload and telemetry event IDs are deterministic per
  service/minute/metric; duplicate ingestion remains safe.

## Probe findings

- `docker-compose.yml` now contains the five demo service databases, Django boot commands and health checks.
- The dashboard receives only runtime telemetry published by the real demo services; it has no synthetic seed command.
- `telemetry/collector-config.yaml` — currently accepts OTLP and writes debug output; it does not
  forward signals to SentinelAI ingestion.
- `backend/demo/views.py` — existing ingestion is JWT-protected, so a machine-to-machine
  collector credential must be designed explicitly rather than reusing browser admin access.

## Rejected alternatives

| Option | Why not |
|---|---|
| Keep five seed names only | Does not test process boundaries, live health or isolated failures. |
| Run five Compose containers from one configurable generic runtime | Reduces build isolation and hides service-specific Django/domain ownership. |
| Publish fixed metric profiles from a small HTTP server | Proves only an ingestion path; it cannot demonstrate real request, ORM, migration or queue behaviour. |
| Expose fault controls on host ports | Broadens local attack surface and makes unsafe activation easier. |
| Let demo services write PostgreSQL directly | Bypasses SentinelAI validation and telemetry contract boundaries. |
| Use super-admin browser JWT for collector ingestion | Couples machine telemetry to a human session and leaks inappropriate authority. |

## API and data contract

- Demo service endpoints: each service exposes `GET /health/` plus bounded DRF domain endpoints.
  Domain mutations pass through a serializer and persist in that service's own database.
- Ingestion path: demo containers publish validated `telemetry.v1` batches to SentinelAI with
  the approved machine credential. OTLP signals remain observable through the Collector; a
  dedicated OTLP-to-envelope adapter is intentionally outside this milestone.
- Telemetry: existing `telemetry.v1` contract; source services never query dashboard aggregates.
- Compatibility: synthetic dashboard seeding is removed. The dashboard is populated only after
  real demo service activity is ingested and aggregated.

## Impact analysis

- Changed: local Compose topology, five service databases, Django migrations, collector
  configuration, ingestion authentication and operator workflow.
- Possibly affected: CI runtime duration, telemetry ingest tests and dashboard service discovery.
- Risk: telemetry delivery can create duplicate events or excessive local cardinality; stable
  event IDs, fixed service names and bounded dimensions mitigate this.
- Recommendation: preserve the secret-derived signature and exec-only fault-control decisions.

## Decision log

| Date | Decision | Why |
|---|---|---|
| 2026-10-27 | Use five independent Docker applications, not seed-only service identities | The project needs a real local microservice topology for observability and fault injection. |
| 2026-10-27 | Keep SentinelAI as a separate telemetry control plane | Demo applications must not bypass telemetry validation, aggregation or dashboard scope. |

## Rules consulted

- `AGENTS.md`
- `specs/README.md`
- `backend/.ai/backend-conventions.md`
- `backend/.ai/testing.md`
- `frontend/.ai/frontend-ai-rules.md`
- `frontend/.ai/project-conventions.md`
