# SentinelAI

SentinelAI is a local, Docker-based observability prototype. Five real demo services create
HTTP, database and queue activity; SentinelAI collects their telemetry, displays service and
system health, and prepares five-minute `features.v1` vectors for a future Isolation Forest
anomaly-detection phase.

The interface is Turkish. Technical terms such as `Service`, `HTTP`, `latency`, `queue`,
`telemetry`, `p95` and `error rate` remain in English.

> This repository is a local development/demo environment. It does not deploy a production
> environment, train an anomaly model yet, or call an LLM API.

## What is included

```text
Vue 3 dashboard
        │
Django REST API + JWT authentication
        │
PostgreSQL ← raw events / minute aggregates / features.v1
        │
Redis + Celery worker + Celery Beat
        │
orders → payments → inventory → notifications → reporting
```

- Five independently containerised Django demo services.
- A real dependency workflow: an order triggers payment authorisation, stock reservation,
  notification and reporting work.
- Real request, ORM and queue telemetry; dashboard values are not seeded or hard-coded.
- Service dashboard and authenticated System Overview.
- Raw-event retention, minute aggregates and idempotent five-minute feature backfill.
- Local-only fault injection utilities for later anomaly evaluation.

## Prerequisites

- Git
- Docker Desktop or Docker Engine with the Compose plugin
- At least 6 GB RAM available for Docker is recommended
- Ports `5174`, `8000`, `4317` and `4318` must be free

No Python, Node.js, PostgreSQL or Redis installation is required on the host.

## Quick start

### 1. Clone the repository

```bash
git clone https://github.com/yasinserhatpeker/sentinel-AI.git
cd sentinel-AI
git switch feature/dashboard-foundation
```

Use `main` instead if the feature branch has already been merged there.

### 2. Create local environment values

```bash
cp .env.example .env
```

Open `.env` and replace all placeholder secrets. They are local-only secrets and must not be
committed. You can generate suitable values with:

```bash
openssl rand -hex 32
```

Required keys:

```dotenv
DJANGO_SECRET_KEY=<a-long-random-local-secret>
JWT_SIGNING_KEY=<a-different-long-random-local-secret>
POSTGRES_DB=sentinelai
POSTGRES_USER=sentinelai
POSTGRES_PASSWORD=<a-local-postgres-password>
```

### 3. Start the complete stack

```bash
docker compose up -d --build
```

The first build downloads images and dependencies, so it can take several minutes. The API
automatically applies version-controlled Django migrations on startup. The demo services create
their own local schemas during their startup sequence.

Check that the core services are running:

```bash
docker compose ps
docker compose logs --tail=50 api worker beat
```

Open the dashboard at [http://localhost:5174](http://localhost:5174).

### 4. Create your local super-admin

User accounts are deliberately not stored in Git or `.env`. Each developer creates their own
local account:

```bash
docker compose exec api python manage.py createsuperuser
```

Enter a username, email and password when prompted, then sign in at `http://localhost:5174`.
The login accepts either username or email.

Authentication uses a short-lived access JWT in browser memory and a rotating refresh JWT in an
`HttpOnly`, `SameSite=Lax` cookie. A page refresh restores the session through the refresh flow.

## First dashboard walkthrough

1. Sign in and select a `Service`.
2. Use **Kayıt oluştur**, **Güncelle**, **Sil**, or a 10/100/1000-record workload button.
3. Wait a few seconds, then click **Yenile**.
4. Inspect real `HTTP`, `Runtime`, `Database` and `Queue` telemetry.

The available demo services are:

| Service | Responsibility |
| --- | --- |
| `orders-api` | Starts the order workflow. |
| `payments-api` | Creates payment authorisations. |
| `inventory-api` | Creates stock reservations. |
| `notifications-api` | Creates and delivers notifications. |
| `reporting-worker` | Queues and completes report jobs. |

The **Sistem özeti** panel shows healthy/degraded service counts, slowest `p95 latency`,
busiest `queue` and the documented dependency chain. `Incident`, `anomaly score` and historical
`fault context` are intentionally shown as unavailable until their later milestones are built.

### What the dashboard metrics mean

- `request count`: number of observed HTTP requests in a measurement window.
- `p50` / `p95` / `p99 latency`: median, slow-tail and worst-tail request durations.
- `error rate`: proportion of observed server-side failures.
- `CPU` / `Memory`: process measurements captured while a real request runs.
- `query latency`: time spent in ORM/database queries for a request.
- `queue depth`: real pending background work; it is not a synthetic counter.

When a metric has not been observed, the UI shows missing/partial data instead of inventing a
zero value.

## Telemetry and ML feature pipeline

```text
Raw telemetry event (30 days)
        ↓
1-minute aggregate (kept until local reset)
        ↓
5-minute features.v1 vector (kept until local reset)
```

Celery Beat aggregates completed minutes every minute, materialises features every five minutes,
and removes only raw events older than 30 days. `features.v1` contains fixed, aggregate-only
columns such as request count, error rate, p95 latency, CPU/memory, database latency and queue
metrics. Missing signals remain `NULL`, not zero.

If you want to materialise the existing local aggregate history immediately, run:

```bash
docker compose exec api python manage.py shell -c '
from demo.models import TelemetryAggregate
from demo.telemetry_ingestion import backfill_feature_windows
first = TelemetryAggregate.objects.order_by("window_start").values_list("window_start", flat=True).first()
last = TelemetryAggregate.objects.order_by("-window_start").values_list("window_start", flat=True).first()
print(backfill_feature_windows(first, last) if first and last else 0)
'
```

Re-running this command is safe: feature rows are upserted, so duplicates are not created.
See [docs/ml-feature-pipeline.md](docs/ml-feature-pipeline.md) for the full contract.

## Development commands

### Rebuild backend code

The core backend runs from its Docker image rather than a bind-mounted source directory. Rebuild
the relevant services after backend changes:

```bash
docker compose up -d --build api worker beat
```

The Vue frontend is bind-mounted for local development; Vite refreshes it automatically.

### Run tests

```bash
docker compose run --rm --build api python manage.py test demo.tests
cd frontend && npm run build
```

### Inspect logs

```bash
docker compose logs -f api
docker compose logs -f worker
docker compose logs -f orders-api
```

### Stop or reset the local environment

```bash
docker compose down
```

To remove **all** local databases, queues, accounts and telemetry, use the destructive reset:

```bash
docker compose down -v
```

Run `docker compose up -d --build` again after a reset and create a new super-admin.

## Troubleshooting

| Symptom | Check |
| --- | --- |
| Dashboard cannot connect | Confirm `docker compose ps` shows `api` and `frontend` running, then open `http://localhost:5174`. |
| Login fails | Create a fresh super-admin with `docker compose exec api python manage.py createsuperuser`. |
| No telemetry appears | Generate an action from the dashboard, wait briefly for the background publish, then refresh. Inspect `docker compose logs orders-api api`. |
| Backend code seems stale | Run `docker compose up -d --build api worker beat`. |
| A port is already in use | Stop the conflicting process or change the host-side port in `docker-compose.yml`. |
| Local data is inconsistent | Use `docker compose down -v` only if you intentionally want a complete reset. |

## Project layout

- `backend/` — Django REST API, authentication, telemetry persistence, Celery tasks and ML
  feature materialisation.
- `frontend/` — Vue 3 + TypeScript operator dashboard.
- `demo-services/` — independently containerised demo applications and their workers.
- `telemetry/` — OpenTelemetry Collector configuration.
- `docs/` — operator, data collection and ML feature-pipeline documentation.
- `specs/` — AI-assisted development records, design decisions and test evidence.

## Current and upcoming scope

Completed: real service workflow, service dashboard, System Overview, raw retention and
`features.v1` materialisation.

Next: Isolation Forest training/scoring, anomaly records, controlled-fault ground truth,
incident correlation, external benchmark datasets and a redacted external LLM analysis API.

## Contribution workflow

Read `AGENTS.md` before changing the repository. Non-trivial changes use the spec lifecycle in
[`specs/README.md`](specs/README.md): `draft → active → verified → done/archive`.

Use `feature/<name>` or `fix/<name>` branches. Changes merge through pull requests; source
branches should be deleted after merging.
