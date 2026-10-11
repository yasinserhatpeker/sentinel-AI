# SentinelAI

SentinelAI is an AI-assisted observability and incident-analysis platform. It ingests
service telemetry, detects anomalies, correlates related signals into incidents, and
produces explainable root-cause hypotheses and investigation suggestions.

## Milestone 1 — 15 October 2026

The first milestone is research, requirements analysis and system design. Its completed
deliverable is `specs/research-system-design/`, covering scope, telemetry contracts,
architecture boundaries, the minimum metric set and controlled fault-injection scenarios.

## Technology direction

Python/Django REST Framework, Vue 3 + TypeScript, PostgreSQL, Redis + Celery,
OpenTelemetry, scikit-learn, an LLM API or local LLM, and Docker.

## Working rules

Read `AGENTS.md` before making changes. Use `specs/README.md` for non-trivial work and
the backend/frontend `.ai/` rules for implementation-specific guidance. The `.ai/` rules
define the project’s AI-assisted development workflow and domain boundaries.
