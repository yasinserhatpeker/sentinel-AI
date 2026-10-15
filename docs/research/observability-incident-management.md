# SentinelAI araştırma kaydı

Tarih: 11 Ekim 2026  
Milestone: Araştırma, gereksinim analizi ve sistem tasarımı  
Durum: 15 Ekim teslimi için karar girdisi

## Sonuç

SentinelAI observability yaklaşımını birbirinden kopuk grafikler olarak değil, ilişkili
telemetry sinyallerinin bütünü olarak ele almalıdır. OpenTelemetry ortak sözlüğü ve
correlation bağlamını sağlar; uygulama normalize edilmiş kanıtları ve türetilmiş
aggregation sonuçlarını saklar; arka plan işçileri detector ve incident correlation
çalıştırır; dashboard ise operatöre zaman çizelgesi sunar. AI analizi ingestion veya
detection kritik yolunda değil, sonraki açıklama katmanında yer almalıdır.

## 1. Observability yaklaşımı

OpenTelemetry traces, metrics, logs ve baggage sinyallerini; HTTP, database ve messaging
işlemleri için ortak semantic convention’ları tanımlar. Bundan şu kararlar çıkar:

1. Sinyaller arasında `trace_id`, `span_id`, service ve deployment bağlamı korunur.
2. Var olan semantic convention alanları yeniden kullanılır; SentinelAI’ye özgü alanlar
   versiyonlanır ve kullanımdan önce belgelenir.
3. Metrics istatistiksel kanıt, traces ve logs ise inceleme kanıtı olarak ele alınır.
4. Metric cardinality kontrol edilir; route template kullanılabilir, ham URL ve kullanıcı
   kimliği metric dimension olamaz.

OpenTelemetry instrumentation ve taşıma katmanıdır; kalıcı sorgu backend’i değildir.
PostgreSQL bu nedenle normalize edilmiş proje kayıtlarını ve demo için gerekli
aggregation’ları saklar. OTLP uyumlu collector ileride domain model değiştirilmeden eklenebilir.

## 2. Incident-management yaklaşımı

SentinelAI aşağıdaki SRE yaklaşımını izler:

1. Tespit: baseline veya threshold’dan ölçülebilir sapmayı bul.
2. Triage: etkilenen service, zaman aralığı, severity ve mevcut kanıtı belirle.
3. Koordinasyon: owner, timeline ve güncellemeleri yaşayan incident state içinde tut.
4. Mitigation: uygulanan aksiyonu ve etkisini kaydet; ilk milestone otomatik remediation yapmaz.
5. Çözüm: sinyal kabul edilen duruma döndüğünde incident’ı kapat.
6. Öğrenme: blameless timeline, kanıt bağlantıları ve takip aksiyonlarını koru.

Incident; anomaly ve evidence ID’lerine bağlı, stateful bir nesne olarak modellenir.
Correlation; zaman yakınlığı, ortak service/deployment bağlamı ve dependency ilişkilerini
kullanır. Her anomaly için incident’a neden dahil edildiği açıklanabilir olmalıdır.

## 3. Teknoloji sınırları

| Teknoloji | SentinelAI sorumluluğu | Açık sınır |
|---|---|---|
| Django REST Framework | Telemetry’yi doğrulamak, kabul etmek ve query API’lerini sunmak | Request path içinde detector veya LLM çağrısı yok |
| PostgreSQL | Ham bounded event, aggregate, anomaly ve incident saklamak | Yüksek hacimden önce partition/retention kararı gerekli |
| Redis | Broker/cache ve kısa süreli worker koordinasyonu | System of record değildir |
| Celery | Periodic aggregation, detection, correlation ve analysis işleri | İşler idempotent olmalı; tek scheduler kullanılmalı |
| OpenTelemetry | Instrumentation sözlüğü, context propagation ve export sınırı | Storage veya incident semantiğinin yerine geçmez |
| Vue 3 | Dashboard, filtreler, grafikler, kanıt ve timeline ekranları | UI’daki gizli aksiyon güvenlik kontrolü değildir |

## 4. Minimum metric seti

İlk demo şu sinyalleri toplar:

- HTTP: request count, latency p50/p95/p99, 4xx/5xx count ve error rate.
- Runtime: CPU utilization, memory utilization ve process restart.
- Database: connection utilization, query latency ve timeout/error count.
- Queue: depth, oldest-message age, enqueue/dequeue rate ve failure count.
- Deployment: deployment ID, version, başlangıç/bitiş zamanı ve değişen service’ler.

Her event schema version, benzersiz event ID, UTC timestamp, environment, service ve
instance taşır. Ham path yerine route template kullanılır. İlk aggregation aralığı bir
dakikadır; ham kanıt dashboard aggregate’ından ayrı tutulur.

## 5. Fault-injection deney planı

Her deney `scenario_id`, hedef service, başlangıç/bitiş zamanı, beklenen etki ve rollback
aksiyonunu taşır. Deney yalnızca açık bir demo/test flag’i ile çalışır.

| Deney | Hipotez | Ana ölçümler | Değerlendirme |
|---|---|---|---|
| Latency injection | Route’a lokal gecikme tail latency ve trace duration’ı artırır | p95/p99, span duration, request rate | detection delay, recall |
| Error burst | Kontrollü 5xx artışı yayılmadan görünür olur | error rate, status count, route | precision, false positive |
| Database slowdown | Dependency bozulması request latency’ye yansır | query latency, timeout, connection use | lead time, correlation quality |
| Queue backlog | Consumer durması queue age/depth artışı olarak önce görünür | depth, oldest age, dequeue rate | detection delay, recovery visibility |

## 5.1 Demo servisleri ve veri seti stratejisi

İlk çalışan deney ortamı; Django REST API, PostgreSQL, Redis, Celery Worker ve Vue 3
arayüzünden oluşan küçük bir sistem olacaktır. Bu bileşenler Docker Compose ile
tekrarlanabilir biçimde çalıştırılır. Amaç üretim ölçeğinde bir uygulama yapmak değil,
normal HTTP/database/queue akışını ve bu akışın kontrollü bozulmasını gözlemlemektir.

Ana veri seti bu ortamdan üretilecektir. Önce normal yük altında telemetry toplanır;
sonra her fault senaryosu tekrarlanır ve `scenario_id` ile başlangıç/bitiş zamanları
etiketlenir. Metric'ler bir dakikalık pencerelere dönüştürülerek `normal`,
`high_latency`, `error_burst`, `db_slowdown` ve `queue_backlog` sınıfları oluşturulur.
Isolation Forest çoğunlukla normal training pencereleriyle fit edilir; fault etiketleri
model başarısını recall, false-positive rate ve detection delay ile ölçmek için saklanır.

Ana verinin yanında dış açık kaynak veri setleri zorunlu benchmark olarak kullanılacaktır.
Exathlon etiketli zaman serilerinde detector değerlendirmesi; Alibaba Cluster Trace
microservice bağımlılıkları ve performans davranışı; LogHub log anomaly ve kanıt analizi;
OpenTelemetry Demo ise Collector ve sinyal uyumluluğu benchmark'ı için kullanılacaktır.
Her veri seti ortak şemaya dönüştürülecek, sonuçlar ayrı raporlanacak ve projeye alınmadan
önce şema, lisans, kişisel veri ve yeniden dağıtım koşulları kontrol edilecektir.

## 6. Uygulama kararları

- Önce deterministic threshold/statistical detection; baseline oluşunca Isolation Forest değerlendirmesi.
- Summary üretmeden önce evidence reference’larını saklama.
- Time window, environment ve service’i birinci sınıf query dimension’ları yapma.
- Redis/Celery ile asenkron çalışma; HTTP ingestion’ı hızlı ve öngörülebilir tutma.
- Basit harici LLM API ile structured AI sonucu üretme: hypothesis, evidence ID, confidence, alternatifler ve sonraki adımlar.
- AI çıktısının sistem durumunu değiştirmesine veya remediation çalıştırmasına izin vermeme.
- Yerel LLM, fine-tuning ve model hosting geliştirmeme.

## Kaynaklar

- [OpenTelemetry Signals](https://opentelemetry.io/docs/concepts/signals/)
- [OpenTelemetry Observability Primer](https://opentelemetry.io/docs/concepts/observability-primer/)
- [OpenTelemetry Semantic Conventions](https://opentelemetry.io/docs/specs/semconv/general/)
- [OpenTelemetry Metrics](https://opentelemetry.io/docs/concepts/signals/metrics/)
- [Google SRE Incident Management Guide](https://sre.google/resources/practices-and-processes/incident-management-guide/)
- [Google SRE Managing Incidents](https://sre.google/sre-book/managing-incidents/)
- [Django REST Framework Throttling](https://www.django-rest-framework.org/api-guide/throttling/)
- [Vue State Management](https://vuejs.org/guide/scaling-up/state-management.html)
- [PostgreSQL Table Partitioning](https://www.postgresql.org/docs/current/ddl-partitioning.html)
- [Redis Streams](https://redis.io/docs/latest/develop/data-types/streams/)
- [Celery Periodic Tasks](https://docs.celeryq.dev/en/main/userguide/periodic-tasks.html)
