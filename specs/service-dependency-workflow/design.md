---
slug: service-dependency-workflow
title: Order-driven service dependency workflow
author: Yasin Serhat Peker
area: platform
status: draft
created: 2026-10-27 15:30
updated: 2026-10-27 15:30
---

# Design — Order-driven service dependency workflow

## Approach

`POST /v1/orders/` persists an order and queues an `orders-worker` task. The task creates a UUID
correlation ID, then uses a bounded internal HTTP client to execute this causal flow:

```text
orders-worker
  → payments-api: authorization keyed by order reference
  → inventory-api: reservation keyed by order reference
  → notifications-api: workflow notification keyed by order reference
  → reporting-worker: report job keyed by order reference
```

The correlation ID is passed through `X-Correlation-ID`; telemetry middleware records a bounded
dimension from that header. Each target command accepts an idempotency key derived from the order
reference. A retry therefore reads the existing domain record rather than creating a duplicate.

The first implementation has ordered, stop-on-failure semantics. A failed downstream call raises
the Celery task for bounded retry and records only the dependency name, HTTP class and correlation
ID in telemetry. No compensation or distributed transaction is attempted in this local demo slice.

## Blocking decisions

### Data ownership and retention

- Status: `confirmed`
- Scope, source and retention/deletion behaviour: each downstream service owns its workflow record;
  records are local demo data and follow the existing local database lifecycle. Raw telemetry keeps
  only bounded technical metadata under the existing retention policy.
- Migration required: yes. New domain state/idempotency fields or models will be generated locally
  by Docker and will not be committed.

### Authentication and query visibility

- Status: `confirmed`
- Access mode and scope: the workflow uses the private Compose network only. Existing user-facing
  demo CRUD behaviour remains unchanged; SentinelAI aggregate queries remain super-admin JWT scoped.
- Denial behaviour: no internal workflow command is host-published; invalid internal payloads return
  a stable 4xx response and no stack trace.

### Mutation, audit and logging

- Status: `confirmed`
- State-changing paths: order creation queues a workflow; each downstream idempotent command may
  create one owned record. Safe logs contain correlation ID, service name and outcome only.
- Audit and safe logging decision: correlation ID and workflow outcome are persisted or emitted as
  bounded technical metadata; request bodies, tokens and credentials are never logged.

### Telemetry contract and privacy

- Status: `confirmed`
- Schema/version and cardinality controls: existing `telemetry.v1` is preserved; correlation IDs are
  UUID-format, generated per workflow and bounded to one dimension value per request chain.
- Redaction and external-egress decision: all telemetry stays in the local Compose topology; no
  customer payload, payment data or external egress is introduced.

### Operational safety

- Status: `confirmed`
- Retry/idempotency, fault-injection controls and rollback: tasks use bounded retries and idempotent
  commands. A failure stops the remaining chain, preserving the primary error. Existing local-only
  fault controls can target a single dependency. Rollback is disabling the workflow task/config and
  restarting the affected local containers; no destructive data command is required.

## Probe findings

- `demo-services/orders-api/orders/views.py` — order creation already dispatches a Celery task.
- `demo-services/*/tasks.py` — each service has a dedicated queue and real completion work.
- `docker-compose.yml` — all services share only the internal Compose network and have independent
  PostgreSQL databases.
- `demo-services/common/middleware.py` — existing request telemetry is the correct correlation
  capture boundary.

## Rejected alternatives

| Option | Why not |
|---|---|
| Browser calls each service separately | Does not create a causal service dependency chain. |
| Fixed workflow telemetry records | Violates the real telemetry requirement. |
| Distributed transaction across databases | Disproportionate complexity for a local observability demo. |
| Public host ports for internal commands | Broadens attack surface without aiding the milestone. |

## API and data contract

- Public endpoint: existing `POST /v1/orders/` retains its response shape and queues the workflow.
- Internal endpoints: service-owned, idempotent commands receive an order reference and
  `X-Correlation-ID`; they return stable success, duplicate-success or validation error shapes.
- Event/schema fields: existing telemetry envelope plus optional bounded `correlation_id` dimension.
- Compatibility: existing CRUD collection/detail routes remain available. The workflow is additive.

## Impact analysis

- Changed: five demo services, common helpers, local operator documentation and local generated
  database schema.
- Possibly affected: queue depth, request counts and service discovery will rise with one order flow.
- Risk: retry can duplicate work if idempotency is incomplete.
- Recommendation: add integration tests for first execution and repeat execution before manual Compose
  verification.

## Decision log

| Date | Decision | Why |
|---|---|---|
| 2026-10-27 | Use an order-triggered Celery workflow with internal HTTP calls | Produces causal, observable cross-service behaviour while preserving independent services. |
| 2026-10-27 | Use order-reference-derived idempotency keys | Allows safe task retry without duplicated domain records. |

## Rules consulted

- `AGENTS.md`
- `specs/README.md`
- `backend/.ai/backend-conventions.md`
- `backend/.ai/basemodel-audit.md`
- `backend/.ai/drf-viewsets.md`
- `backend/.ai/testing.md`
