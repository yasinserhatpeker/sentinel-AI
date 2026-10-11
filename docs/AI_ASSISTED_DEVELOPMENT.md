# AI-assisted development

SentinelAI uses a structured spec-driven AI-assisted development workflow.

## Adopted

- `AGENTS.md` / `CLAUDE.md` route agents to task-specific rules.
- `specs/` keeps requirements, design decisions and tasks together.
- Non-trivial API, model, analysis, route, shared-service and deployment changes require a spec first.
- Specs use explicit acceptance criteria, verification tags, open questions and decision logs.
- Backend and frontend rules are read before implementation patterns are searched.
- Secrets, production payloads and sensitive logs are excluded from source and specs.

## SentinelAI boundaries

- Scope is expressed as environment, service, deployment and time range.
- Authentication and authorization are explicit future API decisions recorded in specs.
- Detection and incident correlation must retain evidence references and reproducible configuration.
- LLM output is bounded, redacted and advisory; it cannot directly execute an operational action.
- Fault injection is restricted to demo/test environments and must be opt-in.

## Working sequence

1. Read `AGENTS.md`, the relevant `.ai/` files and the active spec.
2. Probe the existing implementation before editing.
3. Record contract and architecture changes in the spec.
4. Implement the smallest change that satisfies the criteria.
5. Run the verification listed in `tasks.md` and record its result.
6. Show the diff and proposed commit message before committing.
