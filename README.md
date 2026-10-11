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
OpenTelemetry, scikit-learn, an LLM API or local LLM, and Docker.

## Çalışma kuralları

Değişiklikten önce `AGENTS.md` dosyasını oku. Kapsamlı işler için `specs/README.md`,
uygulama ayrıntıları için backend/frontend `.ai/` kuralları kullanılır. `.ai/` kuralları
AI destekli geliştirme akışını ve SentinelAI domain sınırlarını tanımlar.

## Araştırma

Mevcut milestone araştırması şu dosyada kayıtlıdır:
[`docs/research/observability-incident-management.md`](docs/research/observability-incident-management.md).
