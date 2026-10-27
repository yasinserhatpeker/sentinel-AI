---
slug: telemetry-retention-features
title: Telemetry retention and ML feature pipeline
author: Yasin Serhat Peker
area: telemetry
status: done
created: 2026-10-27 15:45
updated: 2026-10-27 19:58
---

# Design — Telemetry retention and ML feature pipeline

## Blocking decisions
### Data ownership and retention
- Status: `confirmed`
- Scope, source and retention/deletion behaviour: raw events retain 30 days; minute aggregates and derived five-minute features retain locally until environment reset. Feature rows contain aggregates only.
- Migration required: yes; Docker generates local migration files only.
### Authentication and query visibility
- Status: `confirmed`
- Access mode and scope: generation is internal Celery work; future reads use existing scoped JWT APIs.
- Denial behaviour: no public write endpoint.
### Mutation, audit and logging
- Status: `confirmed`
- State-changing paths: idempotent feature upsert keyed by window/service/environment.
- Audit and safe logging decision: log window/service/count only.
### Telemetry contract and privacy
- Status: `confirmed`
- Schema/version and cardinality controls: `features.v1`, fixed metric columns, no raw dimensions.
- Redaction and external-egress decision: local only.
### Operational safety
- Status: `confirmed`
- Retry/idempotency, fault-injection controls and rollback: idempotent upserts; deleting generated local features is recoverable by backfill.
