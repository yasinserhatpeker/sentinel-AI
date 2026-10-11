# AGENTS.md — SentinelAI

This file routes AI-assisted development rules for SentinelAI. The project uses the
spec workflow under `specs/` and the backend/frontend guidance under `.ai/`.

## Project scope

- `backend/` — Django + Django REST Framework API, telemetry ingestion and analysis.
- `frontend/` — Vue 3 + TypeScript dashboard for system health, metrics and incidents.
- `specs/` — English requirements, design decisions and executable task lists.

The technology direction is Python/Django REST, Vue 3 + TypeScript, PostgreSQL,
Redis + Celery, OpenTelemetry, scikit-learn, an LLM provider or local LLM, and Docker.

## Mandatory workflow

1. Read the applicable `.ai/` rule files before searching implementation patterns.
2. Open or update a spec before API, model, shared service, route, analysis or deployment work.
3. Keep telemetry, incident and analysis contracts explicit and versioned.
4. Never commit credentials, tokens, production payloads or unredacted sensitive telemetry.
5. Keep logs free of secrets and personal data; use correlation IDs and bounded payloads.

## SentinelAI security and reliability invariants

- Tenant, service and environment scope are explicit on every telemetry and incident query.
- Ingestion endpoints validate payload shape, timestamps and event size; malformed data fails closed.
- Raw telemetry is retained only as long as the documented retention policy permits.
- LLM prompts contain redacted, bounded context. Model output is advisory and never an automatic authorization.
- Every detection and correlation decision is traceable to input event IDs, model/version and configuration.
- Fault injection is isolated to demo/test environments and cannot target production by default.
- Secrets belong only in environment or secret-management systems, never source, specs or fixtures.

## Git

Do not commit or push until the user approves the proposed commit. Use a task branch
with the `codex/` prefix when a branch is needed. Commit subjects are English and use
`<type>: <short subject>`, followed by a `Spec: <slug>` trailer.

## Precedence

Project security invariants and `specs/README.md` take precedence over copied generic
rules. `frontend/.ai/app.md` takes precedence over the shared frontend conventions.

