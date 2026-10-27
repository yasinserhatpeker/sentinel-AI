---
slug: system-overview
title: System overview dashboard
author: Yasin Serhat Peker
area: frontend
status: done
verification: full
created: 2026-10-27 15:45
updated: 2026-10-27 19:52
branches: core-development
---

# System overview dashboard

## Problem

Operators must inspect services one by one; they lack a bounded, authenticated system-level health view.

## Scope

**In:** a JWT-protected overview contract and Vue view showing service health, highest p95 latency,
deepest queue, latest local fault context, dependency map and placeholders for incidents/anomaly scores
until those modules exist.

**Out:** incident mutation, ML scoring, LLM output and cross-environment access.

**Existing behaviour preserved:** service-scoped dashboard and aggregate API remain unchanged.

## Acceptance criteria

- [x] Overview is explicitly scoped to `local` and returns no raw telemetry. → `auto:test`
- [x] UI has loading, empty, partial and error states. → `manual:ui`
- [x] Dependency map reflects the documented order workflow. → `manual:ui`

## Open questions

None.
