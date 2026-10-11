---
slug: research-system-design
title: Araştırma, gereksinim analizi ve sistem tasarımı
author: Yasin Serhat Peker
area: platform
status: active
created: 2026-10-11 17:05
updated: 2026-10-11 17:05
---

# Karar kapıları

- Model sahipliği: uygulanamaz; bu milestone’da kalıcı domain modeli uygulanmıyor.
- Authentication: uygulanamaz; bu milestone’da HTTP endpoint uygulanmıyor.
- Permission ve görünürlük: uygulanamaz; query yüzeyi uygulanmıyor.
- Mutation, audit ve logging: uygulanamaz; milestone tasarım odaklıdır, event audit aşağıda tanımlıdır.
- Client data protection: onaylandı; hassas telemetry persistence ve LLM context oluşturma öncesi redakte edilir.

# Yaklaşım

OpenTelemetry uyumlu event’ler ingestion sınırı olacaktır. Django REST gelen telemetry’yi
doğrular ve normalize eder; PostgreSQL sorgulanabilir aggregate ve incident state tutar;
Redis/Celery asynchronous aggregation ve detection yürütür; Vue operatör dashboard’unu
sunar. Detector kanıt bağlantılı anomaly kayıtları üretir; correlation service zaman,
service, deployment ve dependency bağlamına göre kayıtları incident altında toplar.

Basit harici LLM API analizi deterministic detection ve correlation sonrasında çalışır.
Redakte edilmiş, sınırlandırılmış context alır; structured hypothesis, evidence reference,
confidence ve önerilen sonraki incelemeleri üretir. Infrastructure üzerinde değişiklik
yapamaz. Yerel LLM, fine-tuning ve model hosting bu projenin kapsamı dışındadır.

# Araştırma bulguları

- OpenTelemetry sinyalleri, semantic convention’ları ve correlation context’i sağlar; kalıcı query backend’i değildir.
- Incident-management için yaşayan incident state, açık sahiplik, timeline kanıtı ve blameless follow-up gerekir.
- Redis Streams/consumer group acknowledgement ve pending-message takibini destekler; PostgreSQL kalıcı kayıt sistemidir.
- Celery beat periodic işleri zamanlar; production’da schedule için tek scheduler kullanılmalıdır.
- PostgreSQL partitioning sonraki ölçek kararıdır; ilk demo bounded raw evidence ve bir dakikalık aggregate kullanır.
- Raporun minimum demo seti HTTP latency/request rate/error rate, CPU/RAM, database bağlantıları ve queue verileridir.

# Veri akışı

```text
Demo service / OTEL collector
        -> telemetry ingestion API
        -> validation + normalization
        -> PostgreSQL raw/aggregate kayıtları
        -> Celery aggregation + detector
        -> anomaly kayıtları
        -> incident correlation
        -> redacted context builder -> LLM analysis
        -> Vue dashboard ve investigation timeline
```

# Minimum telemetry modeli

Her event `schema_version`, `event_id`, `timestamp`, `environment`, `service`, `instance`,
`deployment_id` ve varsa `trace_id` taşır. Değerler numeric veya sınırlandırılmış enum’dur;
payload boyutu sınırlıdır ve raw message alanları persistence öncesi redakte edilir.

| Sinyal | Gerekli ölçümler | İlk aggregation |
|---|---|---|
| HTTP | request count, latency p50/p95/p99, 4xx/5xx count, error rate | 1 dakika / service-route |
| Runtime | CPU utilization, memory utilization, process restart | 1 dakika / service-instance |
| Database | connection usage, query latency, timeout/error count | 1 dakika / service-database |
| Queue | queue depth, oldest-message age, enqueue/dequeue rate, failure count | 1 dakika / queue |
| Deployment | deployment ID, version, başlangıç/bitiş, değişen service’ler | event tabanlı dimension |

# Fault-injection senaryoları

| Senaryo | Kontrollü injection | Beklenen kanıt | Başarı ölçütü |
|---|---|---|---|
| High latency | Tek demo route’una 5 dakika 300–800 ms gecikme | p95/p99 ve trace duration artışı | detection delay ve recall |
| Error burst | Tek route’ta %10–20 5xx | error-rate spike ve deployment bağı | precision ve false-positive rate |
| Database slowdown | Query gecikmesi veya pool capacity düşüşü | DB latency/timeout sonrası request latency | incident lead time ve correlation quality |
| Queue backlog | Consumer durdurma veya processing rate sınırı | depth ve oldest-age artışı | detection delay ve recovery visibility |

Fault injection yalnızca açık demo/test flag’i ile çalışır, scenario ID ve başlangıç/bitiş
zamanını kaydeder ve varsayılan olarak kapalıdır.

# Karar günlüğü

| Tarih | Karar | Gerekçe |
|---|---|---|
| 2026-10-11 | LLM analizinden önce deterministic detection kullanılacak | Ölçülebilir, tekrarlanabilir ve güvenli demo davranışı |
| 2026-10-11 | Yalnızca basit harici LLM API entegrasyonu kullanılacak | Geliştirme ve operasyonel maliyet düşük tutulur; yerel model işletme yükü alınmaz |

# Harici LLM API sınırı

LLM entegrasyonu ayrı bir `AnalysisProvider` arayüzü arkasında tutulur. Provider; redakte
edilmiş incident context’i gönderir ve yalnızca doğrulanmış structured output kabul eder:
`hypotheses`, `evidence_ids`, `confidence`, `alternatives`, `next_steps`. Timeout, retry,
rate limit ve sağlayıcı hatası için fallback olarak template tabanlı açıklama üretilir.
API anahtarı environment/secret store’da tutulur; telemetry ham payload’ı ve hassas alanlar
LLM’e gönderilmez. Yerel LLM, fine-tuning ve model hosting yapılmaz.

# Reddedilen alternatifler

| Alternatif | Reddedilme gerekçesi |
|---|---|
| LLM’i ingestion içinde çağırmak | Kritik path’e latency, maliyet ve nondeterminism ekler |
| Yalnızca pre-aggregated metric saklamak | Incident incelemesi için gerekli kanıt kaybolur |
