---
slug: telemetry-retention-features
title: Telemetry retention and ML feature pipeline
author: Yasin Serhat Peker
area: telemetry
status: done
verification: full
created: 2026-10-27 15:45
updated: 2026-10-27 19:58
branches: core-development
---

# Telemetry retention and ML feature pipeline

## Problem

Raw telemetry will grow without a durable feature layer for anomaly-model training.

## Scope

**In:** explicit raw/aggregate retention tasks, five-minute feature windows, a versioned feature model
and backfill task. **Out:** detector training, scoring and external datasets.

## Acceptance criteria
- [x] Retention removes only expired raw rows and preserves aggregates/features. → `auto:test`
- [x] Feature windows are deterministic and scoped by environment/service. → `auto:test`
- [x] Backfill is idempotent. → `auto:test`

## Open questions
None.
