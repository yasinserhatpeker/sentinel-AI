# Spec Index

**Append-only — never reformat this file.** A row is appended when a spec is created and
edited in place when its status changes; existing rows never move, and there is no sort
order. Two branches adding a spec collide on the last line: keep both rows, in either
order, and change nothing else. Repair: [`README.md`](./README.md) → Operations → Index
(`/spec index`).

**Columns:** `slug` identity, and the dedupe key · `title` · `author` the human who asked
for the work, never an agent · `area` — `README.md` → Frontmatter · `status` `draft` /
`active` / `done` · `updated` as `DD/MM/YYYY HH:mm` · `location` `active` or `archive`.

**Identity** is the slug: active specs live at `specs/<slug>/`, archived ones at
`specs/archive/<YYYY-MM-DD>-<slug>/`.

| slug | title | author | area | status | updated | location |
| --- | --- | --- | --- | --- | --- | --- |
| research-system-design | Research, requirements analysis and system design | Yasin Serhat Peker | platform | active | 11/10/2026 17:05 | specs/research-system-design/ |
