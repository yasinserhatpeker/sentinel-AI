# Spec Index

**Append-only — do not reformat this file.** Add a row when a spec is created and update
the same row when its status changes. Do not move existing rows. Use the index rules in
[`README.md`](./README.md) for repairs.

**Columns:** `slug` identity · `title` · requesting human `author` · `area` · `status`
(`draft` / `active` / `done`) · `updated` (`DD/MM/YYYY HH:mm`) · `location`.

**Identity** is the slug: active specs live at `specs/<slug>/`, archived ones at
`specs/archive/<YYYY-MM-DD>-<slug>/`.

| slug | title | author | area | status | updated | location |
| --- | --- | --- | --- | --- | --- | --- |
| research-system-design | Research, requirements analysis and system design | Yasin Serhat Peker | platform | active | 11/10/2026 17:05 | specs/research-system-design/ |
| demo-telemetry-foundation | Demo telemetry foundation | Yasin Serhat Peker | platform | active | 18/10/2026 16:22 | specs/demo-telemetry-foundation/ |
| ci-pipeline | Local runtime CI pipeline | Yasin Serhat Peker | ci | active | 18/10/2026 17:03 | specs/ci-pipeline/ |
| dashboard-foundation | Local telemetry dashboard foundation | Yasin Serhat Peker | frontend | active | 27/10/2026 14:10 | specs/dashboard-foundation/ |
| telemetry-ingestion | Telemetry ingestion and minute aggregation | Yasin Serhat Peker | telemetry | done | 18/10/2026 17:48 | specs/archive/2026-10-18-telemetry-ingestion/ |
| auth-super-admin-login | Local super-admin JWT authentication | Yasin Serhat Peker | backend | active | 27/10/2026 15:35 | specs/auth-super-admin-login/ |
| demo-microservices | Local demo microservice topology | Yasin Serhat Peker | platform | active | 27/10/2026 14:39 | specs/demo-microservices/ |
| service-dependency-workflow | Order-driven service dependency workflow | Yasin Serhat Peker | platform | active | 27/10/2026 15:45 | specs/service-dependency-workflow/ |
| system-overview | System overview dashboard | Yasin Serhat Peker | frontend | done | 27/10/2026 19:52 | specs/archive/2026-10-27-system-overview/ |
| telemetry-retention-features | Telemetry retention and ML feature pipeline | Yasin Serhat Peker | telemetry | done | 27/10/2026 19:58 | specs/archive/2026-10-27-telemetry-retention-features/ |
