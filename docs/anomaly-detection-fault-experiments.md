# Anomaly detection and controlled fault experiments

Bu doküman 12.11.2026 milestone'unda eklenen `features.v2`, baseline detector'lar,
Isolation Forest lifecycle, controlled fault injection, ground truth, evaluation ve operator
UI akışını açıklar. Tüm çalışma yerel Docker ortamıyla sınırlıdır; telemetry veya model verisi
dış bir servise gönderilmez.

## Uçtan uca veri akışı

```text
Gerçek HTTP / ORM / Celery işlemi
        ↓
telemetry.v1 raw event
        ↓ her tamamlanan dakika
minute aggregate
        ↓ her tamamlanan 5 dakikalık pencere
features.v1 + features.v2
        ↓
Static threshold + Median/MAD + aktif Isolation Forest
        ↓
DetectionDecision / anomaly evidence
        ↓
Fault ground truth ile eşleştirme
        ↓
Precision / Recall / F1 / FPR / detection delay
        ↓
Türkçe operator UI
```

Metric değerleri UI veya test yardımcıları tarafından uydurulmaz. Request latency middleware'den,
query latency Django ORM ölçümlerinden, queue depth Redis'ten ve background work sonuçları gerçek
Celery worker'larından gelir.

## `features.v2` sözleşmesi

`features.v1` geriye uyumluluk için değişmeden kalır. `features.v2`, aynı beş dakikalık service
penceresine şu sabit ve bounded context alanlarını ekler:

- Base: request count, error rate, HTTP/database p95, CPU, memory, queue depth/age/rate ve failed task.
- Time: hour/day cyclic encoding. Saat ve haftanın günü sin/cos değerleriyle temsil edilir; böylece
  örneğin 23:59 ile 00:00 sayısal olarak birbirinden yapay biçimde uzaklaşmaz.
- Lag: 5, 10 ve 15 dakika önceki tamamlanmış feature değerleri.
- Rolling: 15, 30 ve 60 dakikalık geçmiş pencerelerin mean, std, min ve max özetleri.
- Dependency: statik service graph üzerindeki upstream/downstream özetleri ve delta değerleri.

Her satır `schema_version + environment + service + window_start` ile tekildir. Eksik ölçüm
`0` yapılmaz; `NULL` kalır. Bu ayrım, "ölçüm yok" ile "ölçüldü ve sıfır" durumlarının model
tarafından karıştırılmasını önler. Data-quality raporu sample, missing value, duplicate window ve
sequence gap sayılarını aggregate-only biçimde verir.

## Detector katmanları

### Static threshold

Önceden tanımlı, service-aware eşikleri kontrol eden açıklanabilir baseline'dır. Örneğin yüksek
error rate veya p95 latency doğrudan reason code üretir. Basit, hızlı ve sunumda kolay açıklanır;
fakat servislerin normal davranış farklılıklarını tek başına öğrenemez.

### Median/MAD

Geçmiş pencerenin median değerini ve Median Absolute Deviation'ı kullanır. Mean/std yaklaşımına
göre uç değerlerden daha az etkilenir. Yeterli geçmiş sample yoksa veya dispersion sıfırsa karar
zorlamaz; bounded bir `insufficient_history`/uygun reason sonucu verir.

### Isolation Forest

Label gerektirmeyen multivariate anomaly detector'dır. Normal `features.v2` satırlarını çok sayıda
rastgele partition tree içinde ayırır; az sayıda bölmeyle izole edilen sıra dışı gözlemler daha yüksek
anomaly score alır. Lifecycle şöyledir:

1. Explicit environment/service/time scope seçilir.
2. Yalnızca time-ordered normal feature satırları ve sabit feature allowlist kullanılır.
3. Minimum 50 sample gate uygulanır; eksik değerler pipeline içinde deterministik işlenir.
4. Model artifact'ı Git'e değil local Docker volume'a yazılır; metadata ve checksum database'de tutulur.
5. Eğitim modeli otomatik olarak aktif yapmaz. Super-admin açıkça `Aktif et` işlemi yapar.
6. Tamamlanmış feature window scoring'i idempotent decision kaydı üretir.

## Controlled fault ve güvenlik sınırı

Dört allowlisted senaryo vardır:

| Fault type | Hedef etki | Gerçek gözlem |
| --- | --- | --- |
| `high_latency` | Request işleme öncesi bounded delay | HTTP p95 ve request duration yükselir |
| `error_burst` | Seed ile deterministik 503 oranı | 5xx ve error rate yükselir |
| `database_slowdown` | ORM execute wrapper'a bounded delay | Query/request latency yükselir |
| `queue_backlog` | Reporting task tüketimini yavaşlatır | Queue depth, queued job ve oldest age yükselir |

Koruma kuralları:

- Yalnızca `environment=local` ve beş allowlisted demo service kabul edilir.
- Mutation API'leri yalnızca aktif Django super-admin JWT ile çalışır.
- Süre 15–600 saniye; delay en fazla 5000 ms; error probability 0.05–1.0 aralığındadır.
- Core API ile demo service control endpoint'i HMAC-SHA256 imzalı payload ve 30 saniyelik timestamp
  penceresi kullanır. İmza `DJANGO_SECRET_KEY` üzerinden türetilir; ayrı bir ingestion token gerekmez.
- Aynı service üzerinde çakışan experiment reddedilir.
- Stop idempotent'tir. Watchdog expiry veya restart sonrasında fault state temizlenir.
- Her experiment actor, seed, bounded parameter, lifecycle timestamp ve failure reason ile audit edilir.

## Ground truth ve değerlendirme

Experiment durdurulduğunda ilgili beş dakikalık pencereler `normal`, `fault_active` ve `recovering`
olarak etiketlenir. Detector decision'ları aynı service ve aynı window üzerinden bu label'larla
eşleştirilir; gelecek pencere kullanılmaz.

- Precision: anomaly denilen pencerelerin ne kadarı gerçekten fault'tur.
- Recall: gerçek fault pencerelerinin ne kadarı yakalanmıştır.
- F1-score: precision ve recall'un harmonic mean değeridir.
- False-positive rate: normal pencerelerin ne kadarına yanlış alarm verilmiştir.
- Detection delay: ilk fault window ile ilk doğru anomaly kararı arasındaki süredir.
- Recovery delay: recovery başladıktan sonra detector'ın yeniden normal karara dönme süresidir.

Az local sample ile yüksek score görmek modelin genellendiğini kanıtlamaz. Sonuçlar static threshold ve
Median/MAD baseline'larıyla birlikte raporlanmalı; Isolation Forest yalnızca yeterli normal sample ve
tekrarlı fault deneyleri sonrasında karşılaştırılmalıdır.

## LSTM-ready sequence araştırması

Sistem 12 ardışık `features.v2` penceresinden time-ordered sequence journal üretebilir. Train,
validation ve test split'i zaman sırasını korur; random row split yapılmaz. Offline NumPy prototype,
minimum data gate sağlanırsa LSTM encoder benzeri sequence representation ve logistic readout ile
araştırma sonucu üretir. Bu prototype hiçbir zaman otomatik active detector olmaz.

## Operator UI

Login sonrasında beş ekran vardır:

1. **Sistem özeti:** healthy/degraded service, en yavaş p95, en yüksek anomaly score, aktif fault ve dependency chain.
2. **Servis sağlığı:** gerçek HTTP/Runtime/Database/Queue telemetry ve anomaly marker'ları.
3. **Anomalies:** scoped decision listesi, severity, detector/model version, score/threshold, reason ve evidence.
4. **Fault deneyleri:** super-admin kontrollü create/stop/repeat, active warning ve experiment history.
5. **Model değerlendirmesi:** Isolation Forest train/activate lifecycle ve detector metric karşılaştırması.

Arayüz Türkçedir; `Service`, `Anomaly`, `Fault`, `Precision`, `Recall`, `F1-score`, `p95` gibi teknik
terimler İngilizce bırakılmıştır. Loading, empty, error ve partial-data durumları sıfır değer uydurmaz.

## Tekrar üretilebilir doğrulama

Stack ve super-admin hazırken:

```bash
docker compose up -d --build
docker compose exec api python manage.py verify_fault_experiments --duration 15 --queue-jobs 30
# Fault'un bulunduğu beş dakikalık pencere tamamlandıktan sonra:
docker compose exec api python manage.py finalize_fault_evaluations --lookback-minutes 30
```

Komut gerçek demo service endpoint'lerine istek gönderir, her fault'u signed control ile başlatır,
ölçer, durdurur ve ground-truth window sayısını JSON olarak yazar. Active veya recovering başka
experiment varsa güvenlik nedeniyle başlamaz. Recovery süresi iki dakikadır; Celery watchdog bu durumu
tamamlar, ayrıca liste/özet okuması ve yeni deney başlatma işlemi süresi geçmiş kayıtları kendiliğinden
uzlaştırır. Böylece worker kapalıyken kalan eski bir `recovering` kaydı yeni deneyi süresiz engellemez.
Finalizer yalnızca tamamlanmış minute/feature window'larını aggregate eder, baseline decision'ları
idempotent biçimde üretir, ground truth ile eşleştirir ve LSTM-ready sequence journal'ı günceller.

17.11.2026 local smoke kanıtı:

| Scenario | Baseline | Fault gözlemi | Ground truth |
| --- | --- | --- | --- |
| High latency / payments | 102.6 ms, 200 | 513.8 ms, 200 | 6 window |
| Error burst / notifications | 26.7 ms, 200 | 2.9 ms, 503 | 6 window |
| Database slowdown / inventory | 99.2 ms, 200 | 528.1 ms, 200 | 6 window |
| Queue backlog / reporting | depth 0, queued records 0 | depth 10, queued records 30, 201 | 6 window |

Bu tek smoke run doğrulama kanıtıdır; bilimsel model benchmark'ı değildir. Güvenilir detector kıyası için
farklı saatlerde çok sayıda normal pencere, her fault için tekrarlar ve dış benchmark dataset'leri gerekir.

Completed-window finalizer aynı gün 82 minute aggregate, 8 `features.v2` row ve 16 baseline decision
üretti. İlk high-latency, error-burst ve database-slowdown experiment'lerinde static threshold için
Precision/Recall/F1 `1.0/1.0/1.0`, false-positive rate `0.0` ve detection delay `0 s` gözlendi. Bu
değerler yalnızca tek fault window içeren küçük smoke scope'a aittir; model performans iddiası değildir.

Veri sınırlamaları da beklenen biçimde görünür oldu:

- Aynı beş dakikalık window içinde tekrarlanan experiment'ler aynı detector decision'ını paylaştığı için
  bazı ikinci-run sonuçlarında false-positive rate `0.5` oluştu.
- Median/MAD yeterli tarihsel dispersion/sample olmadan anomaly üretmedi; F1 `0.0` kaldı.
- Queue backlog gerçek depth/job artışı üretse de bu kısa run'da completed feature threshold'una
  yansımadı; detector F1 `0.0` kaldı.
- Yalnızca 8 feature row bulunduğu için 12-window sequence journal üretilemedi ve Isolation Forest'ın
  minimum 50 normal sample training gate'i karşılanmadı.

Bu sonuçlar sistemin eksik veriyi saklamadığını ve metric'leri yapay biçimde iyileştirmediğini gösterir.
Bir sonraki veri toplama aşaması en az 50 normal window, service başına farklı saat/gün örnekleri ve her
fault için ayrı beş dakikalık pencerelerde tekrarlı run üretmelidir.

## Test komutları

```bash
docker compose run --rm api python manage.py test demo.tests
PYTHONPATH=demo-services python3 -m unittest common.test_fault
docker compose run --rm frontend npm test -- --run
docker compose run --rm frontend npm run build
docker compose config --quiet
git diff --check
```

Migration notu: repository policy nedeniyle model değişiklikleri için migration dosyası agent tarafından
üretilip commit edilmez. Disposable local Docker başlangıcı gerekli migration state'ini üretir ve uygular.
