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

Create an order and queue its report with the demo token:

```bash
curl -X POST http://localhost:8000/api/orders/ \
  -H "Authorization: Demo <your-local-demo-token>" \
  -H "Content-Type: application/json" \
  -d '{"reference":"ORDER-001","amount":"19.99"}'
```

The OpenTelemetry Collector prints received traces and metrics to its container logs.

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
