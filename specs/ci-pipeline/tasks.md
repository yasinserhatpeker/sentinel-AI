---
slug: ci-pipeline
title: Local runtime CI pipeline
author: Yasin Serhat Peker
area: ci
status: active
created: 2026-10-18 16:50
updated: 2026-10-18 17:03
---

# Tasks — Local runtime CI pipeline

## Phase 0 — Probe and gates

- [x] Read the current branch workflow, Docker Compose topology and applicable spec rules.
- [x] Record that the pipeline is CI only; deployment is out of scope.
- [x] Record all blocking decisions in `design.md`.
- [x] Record the local workflow-command baseline after implementation.

## Phase 1 — Implement

- [x] Add a pull-request and `core-development` push trigger.
- [x] Validate source whitespace and Docker Compose configuration.
- [x] Build/start the local Docker topology and run the focused Django test suite.
- [x] Publish diagnostic Compose logs on failure and always clean up services/volumes.

## Phase 2 — Verification record

| Criterion | Tag | Evidence |
|---|---|---|
| CI syntax and Compose validation | `auto:check` | 2026-10-18: `git diff --check` and `docker compose --env-file .env.example config -q` passed. |
| Docker integration test | `auto:test` | 2026-10-18: `docker compose --env-file .env.example up --detach --build --wait` succeeded; `docker compose --env-file .env.example exec --no-TTY api python manage.py test demo` passed 4/4. |
| GitHub pull-request trigger and cleanup | `manual:github` | 2026-10-18: PR #2 started `Local runtime CI`; run 39134147570 completed successfully. Its unconditional cleanup step removed Compose resources. Push-to-core trigger remains pending until this PR merges. |

- [x] Record every automatic command result.
- [ ] Confirm the proposed commit trailer uses `Spec: ci-pipeline` after user approves a commit.
