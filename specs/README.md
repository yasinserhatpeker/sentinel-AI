# specs/ — SentinelAI

Specs are short, English-language records for non-trivial SentinelAI work. Each active
spec contains `requirements.md`, `design.md` and `tasks.md`.

Open a spec before changing an API, event schema, data model, detector, correlation rule,
LLM context contract, route, shared service/store, deployment configuration or CI behavior.
Small isolated UI, copy, comment or documentation changes may skip a spec.

## Required workflow

1. Read the applicable root and `.ai/` rules.
2. Probe the existing code before writing requirements.
3. Record scope, acceptance criteria, architecture decisions, risks and open questions.
4. Keep `status: draft` until the owner approves implementation.
5. Implement only after the spec is active.
6. Run the listed verification and record results in `tasks.md`.

All three files carry `slug`, `title`, `author`, `area`, `status`, `created` and `updated`.
Requirements also carries `branches` and `verification`. Use `- [ ]` for pending,
`- [x]` for verified and `- [~]` only for a manual criterion with a written reason.
`INDEX.md` is append-only. Completed specs move to `specs/archive/YYYY-MM-DD-slug/`.
Never put credentials, tokens, production payloads or secrets in a spec.
