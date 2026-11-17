# Gerçek veri workload ve model readiness

Bu doküman, SentinelAI'ın Isolation Forest ve offline LSTM prototype için gereken
veriyi yapay timestamp veya doğrudan telemetry kaydı üretmeden nasıl topladığını
açıklar.

## Temel ilke

`workload-runner`, yalnızca demo service'lerin gerçek business HTTP endpoint'lerini
çağırır. Request, ORM, dependency workflow ve queue işlemleri normal application
instrumentation tarafından ölçülür. Runner hiçbir `TelemetryEvent`,
`TelemetryAggregate`, `TelemetryFeature` veya `SequenceJournal` satırını doğrudan
oluşturmaz.

Bu ayrım önemlidir: model, elle verilmiş metric değerlerini değil, gerçekten çalışan
service'lerin oluşturduğu gözlemleri öğrenir.

## Toplanan activity

Her workload cycle aşağıdaki işleri üretir:

- `orders-api`: order oluşturma, okuma ve güncelleme; dependency workflow'u başlatma.
- `payments-api`: payment authorization oluşturma ve okuma.
- `inventory-api`: stock kaydı oluşturma ve okuma.
- `notifications-api`: notification oluşturma ve okuma.
- `reporting-worker`: report oluşturma, queue'ya alma ve sonucu okuma.

Order workflow ayrıca payment, inventory, notification ve reporting service'lerini
birbirine bağlar. Böylece yalnızca bağımsız CRUD trafiği değil, downstream latency,
error propagation ve queue davranışı da gözlemlenir.

## Workload'u başlatma

Ana stack çalışırken bounded workload profile'ını başlatın:

```bash
docker compose --profile workload up -d --build workload-runner
```

Varsayılan çalışma süresi sekiz saat, cycle aralığı 30 saniyedir. Değerler bounded'dır:

- duration: 60–43.200 saniye
- interval: 5–300 saniye
- request timeout: 1–15 saniye

Tekrarlanabilir bir run için örnek:

```bash
WORKLOAD_DURATION_SECONDS=28800 \
WORKLOAD_INTERVAL_SECONDS=30 \
WORKLOAD_SEED=42 \
WORKLOAD_RUN_ID=readiness-local \
docker compose --profile workload up -d --build workload-runner
```

Progress ve request error'larını izleyin:

```bash
docker compose logs -f workload-runner
```

Gerekirse güvenli biçimde durdurun:

```bash
docker compose --profile workload stop workload-runner
```

## Readiness nasıl hesaplanır?

Authenticated super-admin kullanıcı, Models ekranından veya aşağıdaki endpoint'ten
service-scoped readiness bilgisini görebilir:

```text
GET /api/models/v1/readiness/?environment=local&service=orders-api&range=30d
```

Rapor raw payload döndürmez. Şunları verir:

- toplam `features.v2` window sayısı,
- normal kabul edilen Isolation Forest training sample sayısı,
- ilk ve son tamamlanmış window,
- en uzun kesintisiz beş dakikalık window zinciri,
- gap ve missing feature oranı,
- üretilebilecek 12-window sequence sayısı,
- materialize edilmiş train/validation/test journal sayıları,
- Isolation Forest ve LSTM gate durumları,
- LSTM için kalan gerçek window ve tahmini dakika.

## Sabit güvenlik eşikleri

- Isolation Forest: en az 50 normal `features.v2` sample.
- LSTM: 12-window sequence ve en az 60 geçerli sequence.
- 60 sequence için kesintisiz en az 71 adet beş dakikalık feature window gerekir.

Bu eşikler readiness ekranını yeşil göstermek için düşürülmez. Timestamp backfill,
fabricated telemetry veya doğrudan feature insert kullanılmaz. Beş dakikalık gerçek
window nedeniyle sıfırdan yaklaşık 250 dakika sonra Isolation Forest, yaklaşık 355
dakika sonra LSTM veri eşiği oluşur; normal sample exclusion ve gap varsa süre uzar.

## Durumların anlamı

- `collecting`: en az bir model gate'i henüz karşılanmıyor.
- `isolation_forest_ready`: Isolation Forest eğitilebilir, LSTM için veri toplanıyor.
- `lstm_ready`: her iki veri gate'i de karşılandı.
- `partial`: bazı readiness alanları mevcut ancak scope'ta gap veya eksik değer var.
- `error`: readiness isteği tamamlanamadı; API ve worker logları incelenmelidir.

## Fault dönemleri

Controlled fault window'ları ground truth olarak korunur; Isolation Forest training
setine normal sample diye eklenmez. Fault bittikten sonra recovery doğrulanır ve workload
normal veri üretmeye devam eder. Böylece detector evaluation gerçek normal/fault ayrımı
üzerinden yapılır.

## Model lifecycle

Readiness gate'i karşılandıktan sonra Models ekranındaki **Seçili scope ile eğit**
aksiyonu Isolation Forest artifact'ını üretir. Eğitim tamamlandıktan sonra operator
modeli ayrıca **Aktif et** aksiyonuyla live scoring için seçer. Eğitim ile aktivasyonun
ayrı olması, doğrulanmamış bir artifact'ın istemeden canlı kararlara katılmasını önler.

LSTM akışı ayrı ve bilinçli olarak offline'dır:

```text
POST /api/models/v1/lstm-prototype/train/
```

Endpoint bounded environment/service/time scope, minimum 60 sequence, 12-window
sequence length, epoch ve deterministic seed kabul eder. Önce journal'ları idempotent
biçimde materialize eder, sonra chronological train/validation/test split üzerinde
prototype'ı çalıştırır. Response sample sayılarını ve validation/test accuracy'yi
döndürür; `activated` her zaman `false` değerindedir. Bu milestone LSTM'i live detector
olarak aktive etmez.

## Doğrulama

```bash
PYTHONPATH=workload python3 -m unittest workload/test_runner.py
docker compose run --rm --build api python manage.py test demo.tests.test_model_readiness demo.tests.test_analysis_api
docker compose run --rm frontend npm test -- --run
docker compose run --rm frontend npm run build
```
