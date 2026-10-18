---
slug: ci-pipeline
title: Local runtime CI pipeline
author: Yasin Serhat Peker
area: ci
status: active
verification: full
created: 2026-10-18 16:50
updated: 2026-10-18 17:03
branches: feature/ci-cd-pipeline
---

# Local runtime CI pipeline

## Problem

The repository has no automated guard that proves a proposed merge still builds the
local Docker topology or passes the Django demo test suite.

## Scope

**In:** A GitHub Actions CI workflow for pull requests targeting `core-development`
and pushes to that branch; formatting/diff validation; Docker Compose configuration and
build validation; the existing Django demo test suite; guaranteed Docker cleanup.

**Out:** Production, staging or preview deployment; registry publishing; credentials;
external telemetry, LLM or dataset access; frontend checks until a frontend application
exists.

**Existing behaviour preserved:** The system remains a local Docker-based demo. The
workflow uses only synthetic configuration from `.env.example` and creates no persistent
remote resources.

## Acceptance criteria

- [x] A pull request to `core-development` starts a named CI workflow. → `manual:github`
- [ ] A push to `core-development` starts the same CI workflow. → `manual:github`
- [x] CI rejects whitespace errors and invalid Docker Compose configuration. → `auto:check`
- [x] CI builds the local Docker topology and runs `python manage.py test demo` in the API container. → `auto:test`
- [x] CI always removes its Docker Compose services and volumes after a run. → `manual:github`
- [x] No deployment, remote secret or production configuration is introduced. → `manual:doc`

## Affected areas

| Area | Planned change |
|---|---|
| `.github/workflows/` | GitHub Actions CI workflow |
| `specs/ci-pipeline/` | Requirements, design and verification record |
| `specs/INDEX.md` | Append-only draft entry |

## Open questions

None.
