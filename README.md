# SentinelAI

SentinelAI, AI destekli bir observability ve incident-analysis platformudur. Service
telemetry’sini toplar, anomalileri tespit eder, ilişkili sinyalleri incident altında
birleştirir ve açıklanabilir kök neden hipotezleri ile inceleme önerileri üretir.

## Milestone 1 — 15 October 2026

İlk milestone araştırma, gereksinim analizi ve sistem tasarımıdır. Teslimatı;
`specs/research-system-design/` altında kapsamı, telemetry sözleşmelerini, mimari sınırları,
minimum metric setini ve kontrollü fault-injection senaryolarını kapsar.

## Teknoloji yönü

Python/Django REST Framework, Vue 3 + TypeScript, PostgreSQL, Redis + Celery,
OpenTelemetry, scikit-learn, a simple external LLM API, and Docker.

## Monorepo layout

- `backend/` — Django REST demo API, Celery Worker and later telemetry ingestion.
- `frontend/` — Vue dashboard; implemented in the dashboard spec, not the first telemetry foundation.
- `telemetry/` — OpenTelemetry Collector configuration and local signal inspection.
- `specs/` — approved development records and verification evidence.
- Root — Docker Compose and local environment examples.

Shared packages are deliberately absent until a concrete cross-application reuse case exists.

## First local demo

Copy `.env.example` to `.env`, set local-only values, then run:

```bash
docker compose up --build
```

Local demo telemetry uses an HMAC signature derived from `DJANGO_SECRET_KEY`; no separate
telemetry token is stored in `.env`. The raw secret is never rendered in Vue, logged or sent over
HTTP.

Create a local administrator, then sign in with its email and password:

```bash
docker compose exec api python manage.py createsuperuser
```

The command is intentionally interactive: credentials are neither stored in the repository nor
read from environment variables. Each developer may create their own local super-admin account.
After signing in at [http://localhost:5174](http://localhost:5174), the browser keeps the short-lived
access JWT only in memory and sends the rotating refresh JWT as an `HttpOnly` cookie.

For a direct API check, obtain an access JWT through the sign-in flow and use it as a Bearer token:

```bash
curl -X POST http://localhost:8000/api/orders/ \
  -H "Authorization: Bearer <access-jwt>" \
  -H "Content-Type: application/json" \
  -d '{"reference":"ORDER-001","amount":"19.99"}'
```

The OpenTelemetry Collector prints received traces and metrics to its container logs.

## Local dashboard walkthrough

After the stack starts, create records through the five demo service APIs. Each HTTP request
and report task emits telemetry measured during that real execution; no seed command or fixed
metric profile is used.

Open [http://localhost:5174](http://localhost:5174), sign in with a local super-admin, select
one of the five demo services (`orders-api`, `inventory-api`, `payments-api`, `reporting-worker`
or `notifications-api`) and choose a time range. The access JWT remains only in browser memory; a
page refresh obtains a new one via the rotating, database-revocable refresh cookie.

The initial panels show:

- HTTP request count, error rate and p50/p95/p99 latency. **p95** means 95% of sampled
  requests completed at or below that duration.
- Runtime CPU and memory utilisation.
- Database connection usage and query latency.
- Queue depth, oldest-message age, enqueue/dequeue rate and failed task count.

When a metric group has no aggregate point, the UI reports **partial data** rather than
presenting a fabricated zero.

For live service roles and safe fault injection commands, see
[`docs/local-dashboard.md`](docs/local-dashboard.md#live-demo-services-and-fault-injection).

## Çalışma kuralları

Değişiklikten önce `AGENTS.md` dosyasını oku. Kapsamlı işler için `specs/README.md`,
uygulama ayrıntıları için backend/frontend `.ai/` kuralları kullanılır. `.ai/` kuralları
AI destekli geliştirme akışını ve SentinelAI domain sınırlarını tanımlar.

## Araştırma

Mevcut milestone araştırması şu dosyada kayıtlıdır:
[`docs/research/observability-incident-management.md`](docs/research/observability-incident-management.md).

Demo servislerinin çalışma mantığı, fault injection ve veri üretim planı:
[`docs/demo-services-and-data-collection.md`](docs/demo-services-and-data-collection.md).

Ana proje verisi SentinelAI demo ortamında üretilen etiketli telemetry olacaktır.
Buna ek olarak Exathlon, Alibaba Cluster Trace ve LogHub dış benchmark olarak zorunlu
değerlendirme setleri şeklinde kullanılacaktır.
