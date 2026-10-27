# Local telemetry dashboard

The first dashboard is a local-only Vue application at `http://localhost:5174`. It accesses
the Django API through the Vite local development proxy, so the browser calls a same-origin
`/api/...` path. There is no production deployment or external telemetry provider in this
milestone. The access JWT stays in browser runtime memory, while a rotating refresh JWT is kept
in an `HttpOnly` cookie and can be revoked through Django's database-backed token blacklist.

## Start and collect real telemetry

1. Copy `.env.example` to `.env` and set local-only values.
2. Run `docker compose up --build`.
3. Send real requests to the demo microservices. The dashboard shows only telemetry emitted from those requests and from completed background jobs.
4. Run `docker compose exec api python manage.py createsuperuser` and follow the interactive
   prompts. The super-admin's email and password are never placed in `.env` or source control.
5. Open the dashboard, sign in with that account, select the local service and select a time
   range containing the collected data.

The dashboard exposes separate **Kayıt oluştur**, **10 kayıt oluştur**, **100 kayıt oluştur**, **1000 kayıt oluştur**,
**Güncelle** and **Sil** actions for the selected service. The batch actions make real domain
`POST` requests in bounded groups of ten and finish with a real collection `GET`; every created
record schedules its service's own background job. The browser never posts metric values: request
middleware, ORM timing and Celery workers remain the only telemetry producers.

The local Compose stack exposes five real demo services: `orders-api`,
`inventory-api`, `payments-api`, `reporting-worker` and `notifications-api`. Each owns a Django
project and PostgreSQL database. UUID event identities make telemetry delivery idempotent, and
minute aggregation is an idempotent upsert.

## Live demo services and fault injection

After `.env` contains `DJANGO_SECRET_KEY`, `docker compose up --build`
also starts five independently built services. They publish bounded technical telemetry derived
from real HTTP requests, ORM queries and Celery jobs; the dashboard sees it through the core
aggregate API. The service roles are:

- `orders-api` — creates order records at `/v1/orders/`; `orders-worker` processes them.
- `inventory-api` — creates stock records at `/v1/stock/`; `inventory-worker` reconciles them.
- `payments-api` — creates authorization records at `/v1/authorizations/`; `payments-worker`
  settles them.
- `reporting-worker` — creates report jobs at `/v1/reports/`, completed by `reporting-celery`.
- `notifications-api` — creates notification records at `/v1/notifications/`;
  `notifications-worker` delivers them.

Every service owns a named Redis-backed Celery queue. Creation produces a real enqueue event;
the worker produces a dequeue event after it completes domain work. Queue depth is read from Redis
at the measurement point, so a value of `0` means the real worker has already drained the queue,
not that a synthetic value was chosen. **Queue depth** is the number of waiting messages;
**oldest-message age** is how long the oldest waiting message has existed; **enqueue/dequeue rate**
show how quickly work enters/leaves a queue.

Fault injection has no published HTTP endpoint. Target one container from a local terminal:

```bash
docker compose exec orders-api python /app/common/fault.py latency --duration 60
```

For the `reporting-worker` queue backlog scenario, activate the fault inside the Celery
consumer container instead: `docker compose exec reporting-celery python /app/common/fault.py queue-backlog --duration 60`.

Available scenarios are `latency`, `errors`, `runtime-pressure` and `queue-backlog`. The state
expires after 15–600 seconds, can be removed with `--clear`, and a container restart removes it.
Only the named service changes; this lets the dashboard demonstrate isolation rather than a
system-wide artificial outage.

## Read contract

Both endpoints require `Authorization: Bearer <access-jwt>`. Only active Django super-admin
accounts can obtain an access JWT through `POST /api/auth/login/`.

- `GET /api/telemetry/v1/services/?environment=local` lists services with local aggregate
  telemetry.
- `GET /api/telemetry/v1/aggregates/?environment=local&service=<service>&start=<UTC-ISO>&end=<UTC-ISO>`
  returns aggregate points. `start` and `end` are required UTC timestamps; their range must be
  positive and at most 24 hours.

The aggregate response never includes raw telemetry events, trace IDs or dimensions. Each point
contains a minute timestamp, metric/unit, count, min/max/average/last and
p50/p95/p99 statistics. **p50** is the median; **p95** and **p99** are the values at or below
which roughly 95% and 99% of observations fall. They help expose tail latency, where a small
number of very slow requests might be hidden by an average.

The response includes availability booleans for HTTP, runtime, database and queue groups. A
false value means the selected service/range has no point from that group; the UI labels the
scope partial instead of treating the signal as zero.
