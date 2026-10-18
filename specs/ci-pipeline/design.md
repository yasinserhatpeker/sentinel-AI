---
slug: ci-pipeline
title: Local runtime CI pipeline
author: Yasin Serhat Peker
area: ci
status: active
created: 2026-10-18 16:50
updated: 2026-10-18 17:52
---

# Design — Local runtime CI pipeline

## Approach

Create one GitHub Actions workflow named `Local runtime CI`. It runs on pull requests
whose base is `core-development` and on direct pushes to `core-development`. A single
job validates the Compose file, builds and starts the same Docker topology developers
use locally, executes `python manage.py test demo` in the API container, and tears down
all services and volumes with an `always()` cleanup step.

The workflow is CI only. There is intentionally no deployment job, environment,
registry publishing or remote service credential.

## Blocking decisions

### Data ownership and retention

- Status: `not_applicable: CI uses only synthetic local-demo data in ephemeral GitHub runner containers.`
- Scope, source and retention/deletion behaviour: Compose volumes are removed at the end of every run.
- Migration required: no.

### Authentication and query visibility

- Status: `not_applicable: CI does not expose an external application endpoint or query surface.`
- Access mode and scope: the test command runs inside the API service.
- Denial behaviour: a failed command fails the workflow and blocks a required check once configured in the ruleset.

### Mutation, audit and logging

- Status: `confirmed`
- State-changing paths: only ephemeral containers and volumes on the GitHub-hosted runner.
- Audit and safe logging decision: GitHub Actions retains workflow logs; workflow commands contain no credentials or production payload.

### Telemetry contract and privacy

- Status: `not_applicable: Collector output remains inside the ephemeral Compose topology; no signal is exported externally.`
- Schema/version and cardinality controls: no telemetry contract change.
- Redaction and external-egress decision: no external telemetry, LLM or dataset connection.

### Operational safety

- Status: `confirmed`
- Retry/idempotency, fault-injection controls and rollback: concurrency cancels superseded CI runs for the same ref; `always()` cleanup removes Compose resources; no deployment exists to roll back.

## Probe findings

- `docker-compose.yml` — local API, PostgreSQL, Redis, Celery Worker and Collector already form the testable topology.
- `backend/demo/tests/` — `python manage.py test demo` is the current focused backend verification command.
- `AGENTS.md` — feature work starts from `core-development` and merges back through a pull request.

## Rejected alternatives

| Option | Why not |
|---|---|
| Deploy on every merge | There is no production or staging environment in the project scope. |
| Hosted database service in CI | Docker Compose already provides the production-like local dependencies without credentials. |
| Require frontend checks now | The dashboard application has not been implemented yet. |

## API and data contract

- Endpoint(s): no public API change.
- Event/schema fields: no telemetry schema change.
- Query parameters and response shape: no contract change.
- Compatibility: workflow uses the documented existing local startup configuration.

## Impact analysis

- Changed: repository automation and merge confidence.
- Possibly affected: branch rules can later mark this workflow as a required status check.
- Risk: Docker startup timing can make a failing service harder to diagnose.
- Recommendation: publish service logs on failure and always tear down resources.

## Decision log

| Date | Decision | Why |
|---|---|---|
| 2026-10-18 | Implement CI only, with no deployment stage | User confirmed the project is intended to run locally. |
| 2026-10-18 | Exercise the Docker Compose topology in CI | It is the closest available integration check for the local runtime. |
| 2026-10-18 | Skip only the diff-only whitespace check on an initial branch push | GitHub sends an all-zero previous SHA without a valid comparison base. Pull requests and normal pushes retain the full diff check; Docker and test verification still run. |

## Rules consulted

- `AGENTS.md`
- `specs/README.md`
