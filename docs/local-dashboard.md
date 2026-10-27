# Local telemetry dashboard

The first dashboard is a local-only Vue application at `http://localhost:5174`. It accesses
the Django API through the Vite local development proxy, so the browser calls a same-origin
`/api/...` path. There is no production deployment or external telemetry provider in this
milestone. The access JWT stays in browser runtime memory, while a rotating refresh JWT is kept
in an `HttpOnly` cookie and can be revoked through Django's database-backed token blacklist.

## Start and seed

1. Copy `.env.example` to `.env` and set local-only values.
2. Run `docker compose up --build`.
3. Run `docker compose exec api python manage.py seed_dashboard_telemetry --minutes 30`.
4. Run `docker compose exec api python manage.py createsuperuser` and follow the interactive
   prompts. The super-admin's email and password are never placed in `.env` or source control.
5. Open the dashboard, sign in with that account, select the local service and select a time
   range containing the seeded data.

`seed_dashboard_telemetry` accepts `--minutes 5..120` and is deterministic for each
service/minute/metric identity. Repeating it is safe: its UUID-based event identities make
duplicate delivery harmless, and minute aggregation is an idempotent upsert.

## Read contract

Both endpoints require `Authorization: Bearer <access-jwt>`. Only active Django super-admin
accounts can obtain an access JWT through `POST /api/auth/login/`.

- `GET /api/telemetry/v1/services/?environment=local` lists services with local aggregate
  telemetry.
- `GET /api/telemetry/v1/aggregates/?environment=local&service=<service>&start=<UTC-ISO>&end=<UTC-ISO>`
  returns aggregate points. `start` and `end` are required UTC timestamps; their range must be
  positive and at most 24 hours.

The aggregate response never includes raw telemetry events, trace IDs, dimensions or the demo
token. Each point contains a minute timestamp, metric/unit, count, min/max/average/last and
p50/p95/p99 statistics. **p50** is the median; **p95** and **p99** are the values at or below
which roughly 95% and 99% of observations fall. They help expose tail latency, where a small
number of very slow requests might be hidden by an average.

The response includes availability booleans for HTTP, runtime, database and queue groups. A
false value means the selected service/range has no point from that group; the UI labels the
scope partial instead of treating the signal as zero.
