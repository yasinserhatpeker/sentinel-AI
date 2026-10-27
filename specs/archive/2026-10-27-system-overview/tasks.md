---
slug: system-overview
title: System overview dashboard
author: Yasin Serhat Peker
area: frontend
status: done
created: 2026-10-27 15:45
updated: 2026-10-27 19:52
---

# Tasks — System overview dashboard

## Phase 1 — Implement
- [x] Add aggregate-only overview endpoint and tests.
- [x] Add typed overview service and accessible dashboard view.
- [x] Add dependency map and explicit unavailable states.

## Phase 2 — Verification record
| Criterion | Tag | Evidence |
|---|---|---|
| Overview contract | `auto:test` | `docker compose run --rm --build api python manage.py test demo.tests` — 22 tests passed on 27/10/2026 19:52. |
| Overview UI | `manual:ui` | Verified on 27/10/2026 19:52 with local `user` session: health cards, explicit unavailable fault/incident/anomaly states, and `orders → payments → inventory → notifications → reporting` dependency chain were visible. |
