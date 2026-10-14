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

# Problem statement

Before implementation starts, SentinelAI needs a shared technical foundation: scope,
telemetry contract, minimum metric set, architecture boundaries and repeatable demo
faults. Without these decisions, ingestion, detection, correlation and AI analysis may
evolve around incompatible assumptions.

# Acceptance criteria

- [x] Platform goal, scope and non-goals are documented. → `manual:doc`
- [x] End-to-end telemetry flow and service boundaries are documented. → `manual:doc`
- [x] A versioned telemetry model covering HTTP, runtime, database and queue signals is defined. → `manual:doc`
- [x] Technology responsibilities and synchronous/asynchronous boundaries are recorded. → `manual:doc`
- [x] High-latency, error-burst, database-slowdown and queue-backlog scenarios are defined. → `manual:doc`
- [x] Detection and follow-up incident-correlation evaluation metrics are defined. → `manual:doc`
- [x] Open decisions required before the 29 October milestone are listed. → `manual:doc`

# Open questions

There are no open questions for the 15 October design milestone. The final LLM API
provider will be selected in a later milestone; local LLM hosting, fine-tuning and model
hosting are out of scope.
