# Demo servisleri ve veri toplama planı

Tarih: 14 Ekim 2026  
Kapsam: 29 Ekim telemetry ve demo altyapısı hazırlığı

## Amaç

SentinelAI için küçük, tekrarlanabilir ve kontrollü bir gözlemleme laboratuvarı
kurulacaktır. Amaç gerçek bir ürünün bütün işlevlerini uygulamak değil; normal sistem
davranışı üretmek, kontrollü arızalar oluşturmak, telemetry toplamak ve anomaly
detection sonuçlarını ölçmektir.

## Demo mimarisi

```text
Vue 3 arayüzü
        |
        v
Django REST API ---- PostgreSQL
        |
        +------------ Redis ---- Celery Worker
                              |
                              v
                        Arka plan görevleri

Tüm bileşenler -> OpenTelemetry Collector -> telemetry depolama/işleme
```

İlk sürümde gereksiz sayıda bağımsız mikroservis oluşturulmayacaktır. Django tek bir
demo API servisi olarak, Celery ise ayrı worker süreci olarak çalışacaktır. PostgreSQL
kalıcı veri kaynağı; Redis cache ve görev kuyruğu; Vue 3 ise demo ve operasyon
dashboard'unu sunacaktır. Geliştirme ortamı Docker Compose ile tekrarlanabilir biçimde
başlatılacaktır.

## Normal istek akışı

Örnek sipariş veya rapor isteği şu akışı oluşturur:

1. Vue 3, Django REST API'ye istek gönderir.
2. API isteği doğrular ve PostgreSQL'e kayıt yazar veya kayıt okur.
3. Gerekirse Redis cache kullanılır.
4. Uzun süren iş Celery kuyruğuna gönderilir.
5. Celery Worker görevi tamamlar.
6. API, database, Redis ve worker adımları OpenTelemetry ile metric, log ve trace üretir.
7. Collector telemetry'yi ingestion ve aggregation akışına taşır.

## Demo bileşenlerinin ilk kapsamı

### Django REST API

```text
GET  /api/health/
GET  /api/orders/
POST /api/orders/
POST /api/jobs/
GET  /api/metrics/
```

API request path içinde ağır ML veya LLM çalıştırmayacaktır. Telemetry kabulü,
normalization ve hızlı response üretimi API'nin sorumluluğudur.

### PostgreSQL

İlk tablolar `orders`, `jobs`, `system_events` ve telemetry aggregate kayıtlarıdır.
Demo amacıyla sorguya gecikme ekleme, timeout üretme ve kontrollü bağlantı sorunu
oluşturma senaryoları desteklenebilir.

### Redis ve Celery

Redis cache ve broker olarak; Celery Worker ise rapor üretme, bildirim simülasyonu,
sipariş işleme ve periyodik aggregation görevleri için kullanılacaktır. Kuyruğa yük
bindirme, consumer durdurma, görev geciktirme ve görev başarısızlığı kontrollü
deneylerdir.

### Vue 3

İlk ekranlar demo işlemleri, servis durumu, zaman aralığı ve temel metric grafikleri,
anomaly/incident timeline'ı ve yalnızca geliştirme/test ortamında çalışan fault test
kontrolleridir.

## Fault injection tasarımı

Fault injection ayrı bir modül altında tutulacak ve varsayılan olarak kapalı olacaktır.
Her deney `scenario_id`, hedef servis, parametreler, başlangıç/bitiş zamanı ve rollback
bilgisiyle kaydedilecektir.

```text
POST /api/faults/latency/
POST /api/faults/error-burst/
POST /api/faults/db-slowdown/
POST /api/faults/queue-backlog/
POST /api/faults/reset/
```

| Senaryo | Uygulama | Beklenen değişim |
|---|---|---|
| `high_latency` | Bir route'a 300–800 ms gecikme | p95/p99 ve trace süresi artar |
| `error_burst` | Kontrollü 5xx oranı | error rate ve status count artar |
| `db_slowdown` | Sorgu gecikmesi veya pool sınırı | DB latency, timeout ve API latency artar |
| `queue_backlog` | Consumer durdurma veya processing rate sınırı | queue depth ve oldest-message-age artar |

Fault injection production'a erişemez; açık test flag'i, environment kontrolü ve
senaryo kayıtları olmadan çalışmaz.

## Veriyi nasıl üreteceğiz?

Ana veri seti SentinelAI'ın kendi demo ortamından üretilecektir:

1. Normal yük altında 2–4 saat telemetry toplanır.
2. Her fault senaryosu en az üç kez tekrarlanır.
3. Her deneyin başlangıç/bitiş aralığı fault kaydıyla etiketlenir.
4. Metric, log ve trace kayıtları UTC timestamp ile saklanır.
5. Metric'ler bir dakikalık pencerelerde feature tablosuna dönüştürülür.
6. Normal ve fault pencereleri train/test ayrımıyla değerlendirilir.

Önerilen alanlar:

```text
timestamp, service_name, route, request_count, error_rate,
latency_p50, latency_p95, latency_p99, cpu_usage, memory_usage,
db_latency, db_errors, queue_depth, oldest_message_age,
active_tasks, anomaly_label, scenario_id
```

Etiketler `normal`, `high_latency`, `error_burst`, `db_slowdown` ve `queue_backlog`
olacaktır. Fault kayıtları ground truth eşleştirmesi için tutulur; modelin her fault
kaydını otomatik olarak eğitim verisine katması engellenir.

Önerilen dizin:

```text
data/
├── raw/                 # ham metric, log ve trace çıktıları
├── processed/           # bir dakikalık feature pencereleri
├── labels/              # fault başlangıç/bitiş ve etiketler
└── README.md            # veri sözleşmesi ve üretim komutları
```

## Isolation Forest ile kullanım

Isolation Forest normal çalışma dönemlerinden oluşan training verisiyle başlatılır.
Yeni bir dakikalık pencere için anomaly score üretilir. Score tek başına incident
değildir; persistence, ilgili metric'ler ve trace/log kanıtlarıyla birlikte değerlendirilir.

Fault injection etiketleri model başarısını ölçmek içindir: recall, false-positive rate,
detection delay ve fault türleri arasındaki ayırt edicilik hesaplanır.

## Açık kaynak veri setlerinin rolü

Hazır veri setleri ana veri kaynağı olmayacaktır; çoğu SentinelAI'ın metric, dependency
ve fault etiketlerini birebir taşımaz. [Alibaba Cluster Trace](https://github.com/alibaba/clusterdata)
microservice bağımlılıkları ve performans davranışını karşılaştırmak; [LogHub](https://github.com/logpai/loghub)
log anomaly denemeleri yapmak için kullanılabilir. [OpenTelemetry Demo](https://opentelemetry.io/docs/demo/)
ise hazır ML veri seti olarak değil, metric, log ve trace üretimi için yardımcı telemetry
kaynağıdır.

Her dış veri seti alınmadan önce lisans, şema, kişisel veri ve yeniden dağıtım koşulları
kontrol edilir.

## Başarı koşulu

29 Ekim tesliminde en az bir normal çalışma akışı, dört tekrarlanabilir fault senaryosu,
OpenTelemetry Collector bağlantısı, etiketlenmiş örnek telemetry pencereleri ve ilk
dashboard grafikleri çalışır durumda olmalıdır. Isolation Forest deneyleri ve ölçüm
tablosu 12 Kasım anomaly detection milestone'unda tamamlanacaktır.
