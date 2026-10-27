---
slug: demo-microservices
title: Local demo microservice topology
author: Yasin Serhat Peker
area: platform
status: active
verification: full
created: 2026-10-27 10:25
updated: 2026-10-27 10:35
branches: core-development
---

# Local demo microservice topology

## Problem

The current dashboard uses seeded telemetry identities. Those identities demonstrate filtering,
but they are not independently running applications and therefore cannot exercise service
boundaries, inter-service failures or isolated fault injection.

## Scope

**In:** five independently built local Django REST applications — `orders-api`, `inventory-api`,
`payments-api`, `reporting-worker` and `notifications-api`; each service's own domain model,
serializer, view, URL configuration, database schema initialization, health endpoint and bounded domain API;
distinct runtime identities; OpenTelemetry resource attributes; a local telemetry ingestion path;
service-scoped realistic workload; isolated local fault scenarios; Compose health checks and
operator documentation.

**Out:** Kubernetes, service mesh, production deployment, external egress, user-facing demo
service authentication, production payment/order behaviour, distributed transactions, and AI
root-cause analysis.

**Existing behaviour preserved:** the SentinelAI core Django API, dashboard login and explicit
environment/service/time query scope remain the system of record. The Vue dashboard continues to
query only SentinelAI's aggregate API, never a demo service directly.

## Acceptance criteria

- [x] `docker compose up --build` starts five individually named, healthy demo-service
      containers alongside SentinelAI core services. → `auto:compose-test`
- [x] Each demo service has its own Django project/app, source directory, Dockerfile/build
      configuration, database, local schema initialization, service name, `service.name` OpenTelemetry resource
      and health endpoint. → `auto:test`
- [ ] SentinelAI service discovery lists all five services after local workload begins; every
      dashboard aggregate remains bounded by environment, service and time. → `auto:test`
- [ ] Domain behaviours are distinguishable: orders handles order requests, inventory handles
      stock reconciliation, payments handles authorization settlement, reporting processes queued work,
      and notifications delivers notification work. → `manual:api`
- [ ] A local fault can target exactly one service without changing another service's health or
      telemetry identity; all fault controls are unreachable from a production configuration.
      → `auto:test`
- [ ] Telemetry carries only bounded technical fields, service context and generated trace IDs;
      no credentials, real customer data or payment data is emitted. → `auto:test`
- [ ] Runtime telemetry is derived from actual HTTP handling, ORM/database activity and task
      execution; source code contains no dashboard-facing fixed metric profile. → `auto:test`
- [ ] The operator guide explains startup, the five service roles, fault activation/rollback and
      how to observe each service on the dashboard. → `manual:docs`

## Affected areas

| Area | Planned change |
|---|---|
| `demo-services/` | Five independently buildable Django REST service applications. |
| `docker-compose.yml` | Internal service network, health checks and Compose topology. |
| `telemetry/` | Collector route from OTLP signals to SentinelAI ingestion. |
| `backend/demo/` | Machine-to-machine ingestion authentication and contract coverage. |
| `frontend/` | Existing service selector consumes discovered live services; no direct service calls. |
| `docs/` | Local microservice and fault-injection operator guide. |

## Open questions

None. Resolved 2026-10-27: each service owns a separate Django domain model and database;
SentinelAI remains the aggregate-only control plane. The Compose-only
`DJANGO_SECRET_KEY`-derived HMAC signature is used for telemetry, while fault injection is activated only
through `docker compose exec` and no host-published control endpoint is permitted.
