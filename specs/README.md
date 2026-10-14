# specs/ — SentinelAI

Specs are concise English records for substantial SentinelAI work. Each active spec
contains `requirements.md`, `design.md` and `tasks.md`.

API, event schema, data model, detector, correlation rule, LLM context contract, route,
shared service/store, deployment configuration veya CI davranışı değişmeden önce spec açılır.
Küçük ve izole UI, metin, yorum veya dokümantasyon değişiklikleri spec gerektirmeyebilir.

## Required workflow

1. Read the applicable root and `.ai/` rules.
2. Inspect the existing code before writing requirements.
3. Record scope, acceptance criteria, architecture decisions, risks and open questions.
4. Keep `status: draft` until owner approval.
5. Implement only after the spec becomes active.
6. Run listed verification commands and record results in `tasks.md`.

All three files contain `slug`, `title`, `author`, `area`, `status`, `created` and
`updated`. Requirements also contain `branches` and `verification`. Use `- [ ]` for a
pending criterion, `- [x]` for a verified criterion and `- [~]` for a manually justified
criterion. `INDEX.md` is append-only. Move completed specs to
`specs/archive/YYYY-MM-DD-slug/`. Never put credentials, tokens, production payloads or
secrets in a spec.
