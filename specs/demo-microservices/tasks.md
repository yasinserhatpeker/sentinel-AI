---
slug: demo-microservices
title: Local demo microservice topology
author: Yasin Serhat Peker
area: platform
status: active
created: 2026-10-27 10:25
updated: 2026-10-27 15:00
---

# Tasks — Local demo microservice topology

## Phase 0 — Probe and gates

- [x] Read applicable backend, frontend, project and spec rules.
- [x] Confirm the five-service microservice direction and core/control-plane boundary.
- [x] Confirm the dedicated machine telemetry credential decision.
- [x] Confirm exec-only local fault activation and rollback decision.
- [x] Record baseline Compose startup behaviour. Collector-to-envelope adaptation remains explicitly out of scope.

## Phase 1 — Implement

- [x] Replace the synthetic HTTP server with five independently buildable Django REST projects.
- [x] Add one owned model, serializer, view, URL configuration and local schema initialization per service.
- [x] Provision separate Compose PostgreSQL databases and service-owned schema initialization commands.
- [x] Add domain health and bounded demo routes to each service.
- [x] Set unique service identities; keep the Collector as a separately inspectable OTLP boundary.
- [x] Add approved machine-to-machine ingestion authentication without weakening browser JWT access.
- [x] Add local domain workload and telemetry measured from HTTP, ORM and task execution.
- [x] Add one Redis-backed Celery queue and dedicated worker to every service with queued work.
- [x] Add isolated fault injection controls, automatic expiry and restart rollback.
- [x] Update Compose health checks and local operator documentation.
- [x] Add ingestion authentication regression coverage and record live domain, ingestion and isolation verification.

## Phase 2 — Verification record

| Criterion | Tag | Evidence |
|---|---|---|
| Five healthy containers | `auto:compose-test` | `docker compose up -d --build --wait ...` completed successfully on 27/10/2026. |
| Live service discovery and aggregate telemetry | `auto:test` | One real POST per service yielded five raw service identities and five minute-aggregate service identities. |
| Isolated fault activation and rollback | `auto:test` | `orders-api` returned 503 under `errors`; `inventory-api` remained 201; the fault was cleared. |
| Service roles and dashboard walkthrough | `manual:api` / `manual:docs` | Real order, stock, authorization, notification and report-job mutations returned 201; report job completed via Celery. |

- [x] Record every automatic command result.
- [ ] Confirm the commit trailer uses `Spec: demo-microservices` after commit approval.
