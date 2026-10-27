---
slug: system-overview
title: System overview dashboard
author: Yasin Serhat Peker
area: frontend
status: done
created: 2026-10-27 15:45
updated: 2026-10-27 19:52
---

# Design — System overview dashboard

## Approach

The backend derives a bounded local summary from minute aggregates. The frontend renders cards and
a static dependency map; missing incident/anomaly modules are shown as unavailable, never zero.

## Blocking decisions

### Data ownership and retention
- Status: `confirmed`
- Scope, source and retention/deletion behaviour: derived response only; no new retained UI data.
- Migration required: no
### Authentication and query visibility
- Status: `confirmed`
- Access mode and scope: existing super-admin JWT, explicit local environment.
- Denial behaviour: unauthenticated requests are denied.
### Mutation, audit and logging
- Status: `not_applicable: read-only overview`
### Telemetry contract and privacy
- Status: `confirmed`
- Schema/version and cardinality controls: versioned overview response with aggregate-only values.
- Redaction and external-egress decision: no raw events or external egress.
### Operational safety
- Status: `confirmed`
- Retry/idempotency, fault-injection controls and rollback: read-only; rollout is reversible frontend/backend code.

## Rules consulted
- `AGENTS.md`
- `specs/README.md`
- `frontend/.ai/frontend-ai-rules.md`
