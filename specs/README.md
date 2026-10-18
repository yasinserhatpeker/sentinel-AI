# specs/ — SentinelAI

Specs are concise English records for non-trivial SentinelAI work. Each active spec has
`requirements.md`, `design.md` and `tasks.md`. Copy `specs/_template/`; never edit the
templates while working on a spec.

```text
specs/
  _template/                         reusable three-file starter
  <slug>/                             active draft or approved spec
  archive/YYYY-MM-DD-<slug>/          completed spec
  INDEX.md                            append-only index
  BACKLOG.md                          post-hotfix follow-up only
```

## When a spec is required

A spec is required before a new Django model, API endpoint, telemetry schema, ingestion
contract, Celery task, detector/correlation/LLM contract, OpenTelemetry configuration,
shared frontend service/store/type, route/screen, Docker or deployment/CI change. A
single-file isolated copy or documentation edit normally does not need one.

## Lifecycle

1. **Open.** Read applicable rules and relevant source first. Create `specs/<slug>/`
   from `_template/`, set `status: draft`, append an INDEX row and write no application code.
2. **Approve.** Report assumptions, open questions and pending blocking gates. Only the
   user's explicit approval changes all three files to `status: active`.
3. **Implement.** Work only while the spec is active; keep `tasks.md` current.
4. **Verify.** Run each `auto:*` acceptance-criterion command and record output or a
   baseline limitation in `tasks.md` → Phase 2. Manual criteria stay pending until tested.
5. **Done.** Before archiving, inspect the archive gate below. If every check passes,
   set status to `done`, move the folder to `archive/YYYY-MM-DD-<slug>/` and edit its
   existing INDEX row in place. Otherwise move nothing.

Agents report migration requirements in the spec and verification record; they do not
generate or commit migration files. Local Docker development generates migrations per
environment outside the source tree.

## Frontmatter and status

All three files use `slug`, `title`, `author`, `area`, `status`, `created` and `updated`.
`requirements.md` also has `branches` and `verification`. `author` is the human requester,
never an agent. Status progresses only `draft` → `active` → `done`. Dates use local
`YYYY-MM-DD HH:mm` time. `INDEX.md` is append-only and never regenerated.

Use `- [ ]` for pending, `- [x]` for verified and `- [~]` only for a manual criterion
with its reason, approver and date. An automatic criterion cannot be waived.

## Blocking gates

`design.md` must mark each gate `confirmed`, `pending` or `not_applicable: <reason>`.
Any applicable `pending` gate blocks implementation.

| Gate | Decision required |
|---|---|
| Data ownership and retention | Scope, source, retention/deletion behaviour and migrations |
| Authentication and query visibility | Access mode, service/environment/time scope and denial behaviour |
| Mutation, audit and logging | State-changing paths, audit trail and safe log content |
| Telemetry contract and privacy | Schema/version, cardinality, redaction and external egress |
| Operational safety | Fault-injection controls, retry/idempotency and rollback |

Do not infer a gate from a file name or neighbouring code. Record an unconfirmed decision
as an `assumption:` or open question instead.

## Archive gate

Before closing a spec, verify all of the following in the files themselves:

- No pending task remains in `tasks.md`.
- Every acceptance criterion is verified or has a valid manual waiver.
- All blocking gates are confirmed or not applicable with a reason.
- No open `assumption:` remains.
- Open questions are `None.` or explicitly resolved with a date.
- Every `auto:*` command result is recorded in `tasks.md` → Phase 2.
- No stale reference to a superseded decision remains.

## Git and secrets

Use an English commit subject and `Spec: <slug>` trailer. Do not commit or push before
user approval. Specs must never include credentials, tokens, raw production payloads,
unredacted telemetry or personal data.
