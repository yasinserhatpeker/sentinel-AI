---
slug: research-system-design
title: Research, requirements analysis and system design
author: Yasin Serhat Peker
area: platform
status: active
created: 2026-10-11 17:05
updated: 2026-10-11 17:05
branches: codex/sentinelai-foundation
verification: full
---

# Problem

SentinelAI needs a shared technical baseline before implementation: a clear scope,
telemetry contract, minimum metric set, architecture boundary and repeatable demo faults.
Without these decisions, ingestion, detection, correlation and AI analysis will evolve
against incompatible assumptions.

# Acceptance criteria

- [x] The platform goal, in-scope capabilities and explicit non-goals are documented. → `manual:doc`
- [x] The end-to-end telemetry flow and service boundaries are documented. → `manual:doc`
- [x] A versioned minimum telemetry model covers HTTP, runtime, database and queue signals. → `manual:doc`
- [x] Technology responsibilities and synchronous/asynchronous boundaries are recorded. → `manual:doc`
- [x] Controlled high-latency, error-burst, database-slowdown and queue-backlog scenarios are defined. → `manual:doc`
- [x] Detection and later incident-correlation evaluation metrics are defined. → `manual:doc`
- [x] Open decisions required before the 29 October milestone are listed. → `manual:doc`

# Open questions

None for the 15 October design milestone. Provider selection for the LLM and production
retention values remain implementation decisions tracked in the next milestone.
