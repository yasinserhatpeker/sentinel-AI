# AGENTS.md — SentinelAI

This file routes AI-assisted development rules for SentinelAI. The project uses the
spec workflow under `specs/` and the backend/frontend guidance under `.ai/`.

## Project scope

- `backend/` — Django + Django REST Framework API, telemetry ingestion and analysis.
- `frontend/` — Vue 3 + TypeScript dashboard for system health, metrics and incidents.
- `telemetry/` — OpenTelemetry Collector configuration and local telemetry tooling.
- `specs/` — English requirements, design decisions and executable task lists.

SentinelAI is a monorepo. Root configuration owns the local Docker topology and shared
developer tooling; each application owns its implementation and tests. Backend/frontend
contracts are explicit and versioned; a shared package is added only when real reuse
appears.

The technology direction is Python/Django REST, Vue 3 + TypeScript, PostgreSQL,
Redis + Celery, OpenTelemetry, scikit-learn, a simple external LLM API, and Docker.

## Mandatory workflow

1. Read the applicable `.ai/` rule files before searching implementation patterns.
2. Open or update a spec before API, model, shared service, route, analysis or deployment work.
3. Keep telemetry, incident and analysis contracts explicit and versioned.
4. Never commit credentials, tokens, production payloads or unredacted sensitive telemetry.
5. Keep logs free of secrets and personal data; use correlation IDs and bounded payloads.

## Spec lifecycle

The full process is in `specs/README.md`; this is only a pointer. Significant work uses
an English three-file spec. An agent opens it as `draft`, reports decisions, assumptions,
pending gates and open questions, then stops. Only explicit user approval changes it to
`active` and permits implementation. When all acceptance criteria and archive checks pass,
the spec moves to `specs/archive/YYYY-MM-DD-slug/` as `done`.

## SentinelAI security and reliability invariants

- Tenant, service and environment scope are explicit on every telemetry and incident query.
- Ingestion endpoints validate payload shape, timestamps and event size; malformed data fails closed.
- Raw telemetry is retained only as long as the documented retention policy permits.
- External LLM API prompts contain redacted, bounded context. Model output is advisory and never an automatic authorization.
- Local LLM hosting, fine-tuning and self-managed model serving are out of scope.
- Every detection and correlation decision is traceable to input event IDs, model/version and configuration.
- Fault injection is isolated to demo/test environments and cannot target production by default.
- Secrets belong only in environment or secret-management systems, never source, specs or fixtures.

## Git

Do not commit or push until the user approves the proposed commit. `main` is the protected
release branch. `core-development` is the protected integration branch: create
`feature/<topic>` branches for new functionality and `fix/<topic>` branches for bug fixes
from it, then open merge requests back to `core-development`. Delete the source branch
after its pull request is merged. Commit
subjects are English and use `<type>: <short subject>`, followed by a `Spec: <slug>`
trailer. A completed spec is archived only after its archive gate passes.

Agents never generate or commit migration files. A required model-state change is
recorded in its spec; local Docker development generates migrations per environment
outside the source tree.

## Precedence

Project security invariants and `specs/README.md` take precedence over copied generic
rules. `frontend/.ai/app.md` takes precedence over the shared frontend conventions.
