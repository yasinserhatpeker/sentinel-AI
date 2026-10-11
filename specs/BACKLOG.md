# Backlog — captured work not yet promoted to a spec

**This is a buffer, not an archive. Empty is its healthy state.**

Only one kind of entry belongs here: **work whose root cause is worth remembering, but for
which no spec could be written at the time.** Typically production hotfixes — captured
right after the fire is out, while the context is fresh.

What does **not** belong here:

- Trivial fixes (single file, isolated, no export/signature change) → the commit message is enough
- Work that can go through the normal flow → open `/spec <slug>` directly
- Planned work → this is not a todo list; it captures what already happened

## Entry format

```md
- YYYY-MM-DD · `<file or area>` · <root cause, one sentence>.
  Patch: <what was done>. → worth a spec | not worth it
```

Entries never contain credentials, tokens, key material or production payloads.

## Lifecycle

Every entry leaves by becoming a spec or by being deleted — never a third way. The pass
that does it: [`README.md`](./README.md) → Operations → Sweep (`/spec sweep`).

## Related

- When a commit deliberately ships without a spec, mark it: `Spec: none (hotfix)`
- Process: [`README.md`](./README.md) → Hotfixes

---

## Open entries
