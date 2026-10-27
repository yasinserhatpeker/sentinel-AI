---
slug: service-dependency-workflow
title: Order-driven service dependency workflow
author: Yasin Serhat Peker
area: platform
status: draft
verification: full
created: 2026-10-27 15:30
updated: 2026-10-27 15:30
branches: core-development
---

# Order-driven service dependency workflow

## Problem

The local services currently generate useful independent telemetry, but their domain actions do
not form a realistic business flow. Observability and later anomaly analysis need a bounded,
traceable chain where one order causes work in payments, inventory, notifications and reporting.

## Scope

**In:** an order-triggered asynchronous workflow; a correlation ID propagated across service calls;
idempotent internal domain commands; inventory reservation, payment authorization, notification
delivery and report-job creation; service-to-service timeout/error handling; workflow outcome
telemetry derived from real calls; integration and retry verification; local operator documentation.

**Out:** distributed transactions, sagas with compensation, production payment processing, user-facing
demo-service authentication, public orchestration endpoints, external message brokers, incident/ML/LLM
logic, and Kubernetes deployment.

**Existing behaviour preserved:** each service remains independently runnable with its own database
and Celery worker. Existing CRUD routes continue to work. SentinelAI core remains the telemetry
control plane and dashboard aggregate API; no fixed dashboard metrics are introduced.

## Acceptance criteria

- [ ] Creating one order asynchronously starts one correlated workflow across payments, inventory,
      notifications and reporting. → `auto:integration-test`
- [ ] Every downstream command is idempotent: re-running the same order workflow creates no duplicate
      authorization, reservation, notification or report job. → `auto:test`
- [ ] A downstream timeout or non-success response makes the workflow fail safely, emits bounded
      failure telemetry and does not expose internal errors to the public order API. → `auto:test`
- [ ] Generated telemetry carries a bounded correlation ID dimension across the causal service flow,
      without leaking request bodies, credentials or customer data. → `auto:test`
- [ ] Local Docker verification shows an order reaches payment, inventory, notification and reporting
      through actual HTTP/ORM/Celery activity. → `manual:compose`
- [ ] Documentation explains the call order, retry/idempotency behaviour and local failure recovery.
      → `manual:docs`

## Affected areas

| Area | Planned change |
|---|---|
| `demo-services/orders-api/` | Durable workflow task and order workflow state. |
| `demo-services/inventory-api/` | Idempotent inventory reservation command and domain record. |
| `demo-services/payments-api/` | Idempotent authorization command keyed by order reference. |
| `demo-services/notifications-api/` | Idempotent workflow notification command. |
| `demo-services/reporting-worker/` | Idempotent workflow report command. |
| `demo-services/common/` | Bounded internal HTTP client, correlation propagation and telemetry helpers. |
| `docs/` | Local workflow operator guide. |

## Open questions

None. The local-only workflow uses the existing internal Compose network and explicit idempotency
keys; no public service authentication is introduced in this slice.
