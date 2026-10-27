# SentinelAI

SentinelAI, yerel Docker ortamında çalışan bir observability prototipidir. Beş gerçek demo servisinin ürettiği HTTP, database ve queue aktivitesinden telemetry toplar; service ve system health bilgisini gösterir; ilerideki Isolation Forest anomaly detection aşaması için beş dakikalık `features.v1` vektörleri hazırlar.

Arayüz Türkçedir. `Service`, `HTTP`, `latency`, `queue`, `telemetry`, `p95` ve `error rate` gibi teknik terimler İngilizce kalır.

> Bu repository yerel development/demo ortamı içindir. Production deployment içermez; henüz anomaly model eğitimi veya LLM API çağrısı yapmaz.

## İçerik

```text
Vue 3 dashboard
        │
Django REST API + JWT authentication
        │
PostgreSQL ← raw event / minute aggregate / features.v1
        │
Redis + Celery worker + Celery Beat
        │
orders → payments → inventory → notifications → reporting
```

- Birbirinden bağımsız container'larda çalışan beş Django demo service.
- Gerçek dependency workflow: sipariş, payment authorization, stock reservation, notification ve reporting işini tetikler.
- Gerçek request, ORM ve queue telemetry'si; dashboard değerleri seed edilmiş veya hard-coded değildir.
- Service dashboard ve authentication gerektiren System Overview ekranı.
- Raw event retention, minute aggregate ve idempotent beş dakikalık feature backfill.
- İlerideki anomaly evaluation için yalnızca local ortamda çalışan fault injection yardımcıları.

## Gereksinimler

- Git
- Docker Desktop veya Compose plugin'i ile Docker Engine
- Docker için en az 6 GB boş RAM önerilir
- `5174`, `8000`, `4317` ve `4318` portları boş olmalıdır

Host makinede Python, Node.js, PostgreSQL veya Redis kurulumu gerekmez.

## Hızlı başlangıç

### 1. Repository'yi klonlayın

```bash
git clone https://github.com/yasinserhatpeker/sentinel-AI.git
cd sentinel-AI
git switch feature/dashboard-foundation
```

Feature branch `main` ile merge edildiyse `feature/dashboard-foundation` yerine `main` kullanın.

### 2. Yerel environment değerlerini oluşturun

```bash
cp .env.example .env
```

`.env` dosyasını açıp tüm placeholder secret değerlerini değiştirin. Bunlar yalnızca yerel ortam içindir ve Git'e commit edilmemelidir. Uygun bir secret üretmek için:

```bash
openssl rand -hex 32
```

Zorunlu anahtarlar:

```dotenv
DJANGO_SECRET_KEY=<uzun-rastgele-yerel-secret>
JWT_SIGNING_KEY=<farkli-uzun-rastgele-yerel-secret>
POSTGRES_DB=sentinelai
POSTGRES_USER=sentinelai
POSTGRES_PASSWORD=<yerel-postgres-parolasi>
```

### 3. Tüm stack'i başlatın

```bash
docker compose up -d --build
```

İlk build image ve dependency indirdiği için birkaç dakika sürebilir. API açılırken version-controlled Django migration'larını otomatik uygular. Demo servisler de başlangıç sırasında kendi yerel schema'larını oluşturur.

Ana servislerin çalıştığını kontrol edin:

```bash
docker compose ps
docker compose logs --tail=50 api worker beat
```

Dashboard'u [http://localhost:5174](http://localhost:5174) adresinden açın.

### 4. Yerel super-admin hesabınızı oluşturun

Kullanıcı hesapları Git veya `.env` içinde tutulmaz. Her geliştirici kendi yerel hesabını oluşturur:

```bash
docker compose exec api python manage.py createsuperuser
```

İstenen username, e-posta ve parolayı girin; ardından `http://localhost:5174` adresinden giriş yapın. Login ekranı username veya e-posta kabul eder.

Authentication, browser memory içinde kısa ömürlü access JWT; `HttpOnly`, `SameSite=Lax` cookie içinde dönen refresh JWT kullanır. Sayfa yenilenince refresh flow aracılığıyla oturum geri yüklenir.

## İlk dashboard kullanımı

1. Giriş yapın ve bir `Service` seçin.
2. **Kayıt oluştur**, **Güncelle**, **Sil** veya 10/100/1000 kayıtlık workload butonlarından birini kullanın.
3. Birkaç saniye bekleyip **Yenile** butonuna basın.
4. Gerçek `HTTP`, `Runtime`, `Database` ve `Queue` telemetry'sini inceleyin.

Kullanılabilir demo servisler:

| Service | Sorumluluk |
| --- | --- |
| `orders-api` | Sipariş workflow'unu başlatır. |
| `payments-api` | Payment authorization kayıtlarını oluşturur. |
| `inventory-api` | Stock reservation kayıtlarını oluşturur. |
| `notifications-api` | Notification oluşturur ve iletir. |
| `reporting-worker` | Report job'larını queue'ya alır ve tamamlar. |

**Sistem özeti** paneli healthy/degraded service sayısını, en yavaş `p95 latency` değerini, en yoğun `queue`yu ve tanımlı dependency chain'i gösterir. `Incident`, `anomaly score` ve geçmiş `fault context` alanları, ilgili milestone'lar henüz tamamlanmadığı için bilinçli olarak unavailable gösterilir.

### Dashboard metrikleri ne anlama gelir?

- `request count`: ölçüm penceresinde gözlemlenen HTTP request sayısı.
- `p50` / `p95` / `p99 latency`: request sürelerinin median, slow-tail ve worst-tail değerleri.
- `error rate`: gözlemlenen server-side failure'ların oranı.
- `CPU` / `Memory`: gerçek request çalışırken yakalanan process ölçümleri.
- `query latency`: bir request içindeki ORM/database query süreleri.
- `queue depth`: gerçek bekleyen background work sayısıdır; yapay bir sayaç değildir.

Bir metrik henüz gözlemlenmemişse arayüz sıfır değer uydurmak yerine eksik/partial data gösterir.

## Telemetry ve ML feature pipeline

```text
Raw telemetry event (30 gün)
        ↓
1-minute aggregate (local reset'e kadar saklanır)
        ↓
5-minute features.v1 vector (local reset'e kadar saklanır)
```

Celery Beat tamamlanan dakikaları her dakika aggregate eder, her beş dakikada feature materialization çalıştırır ve yalnızca 30 günden eski raw event'leri siler. `features.v1`; request count, error rate, p95 latency, CPU/memory, database latency ve queue metric'leri gibi sabit aggregate-only column'lar içerir. Eksik sinyaller sıfır yerine `NULL` kalır.

Var olan yerel aggregate geçmişini hemen materialize etmek için:

```bash
docker compose exec api python manage.py shell -c '
from demo.models import TelemetryAggregate
from demo.telemetry_ingestion import backfill_feature_windows
first = TelemetryAggregate.objects.order_by("window_start").values_list("window_start", flat=True).first()
last = TelemetryAggregate.objects.order_by("-window_start").values_list("window_start", flat=True).first()
print(backfill_feature_windows(first, last) if first and last else 0)
'
```

Bu komutu tekrar çalıştırmak güvenlidir: feature row'ları upsert edildiğinden duplicate oluşmaz. Ayrıntılı sözleşme için [docs/ml-feature-pipeline.md](docs/ml-feature-pipeline.md) dosyasına bakın.

## Development komutları

### Backend kodunu yeniden build edin

Ana backend, bind-mounted source directory yerine Docker image içinden çalışır. Backend değişikliklerinden sonra ilgili servisleri yeniden build edin:

```bash
docker compose up -d --build api worker beat
```

Vue frontend local development için bind-mounted çalışır; Vite değişiklikleri otomatik yeniler.

### Testleri çalıştırın

```bash
docker compose run --rm --build api python manage.py test demo.tests
cd frontend && npm run build
```

### Logları inceleyin

```bash
docker compose logs -f api
docker compose logs -f worker
docker compose logs -f orders-api
```

### Yerel ortamı durdurun veya sıfırlayın

```bash
docker compose down
```

Tüm yerel database'leri, queue'ları, hesapları ve telemetry verilerini silmek için aşağıdaki yıkıcı reset komutunu kullanın:

```bash
docker compose down -v
```

Reset sonrasında `docker compose up -d --build` komutunu yeniden çalıştırın ve yeni bir super-admin oluşturun.

## Sorun giderme

| Belirti | Kontrol |
| --- | --- |
| Dashboard bağlanamıyor | `docker compose ps` çıktısında `api` ve `frontend` servislerinin çalıştığını doğrulayın, sonra `http://localhost:5174` adresini açın. |
| Login başarısız | `docker compose exec api python manage.py createsuperuser` ile yeni bir super-admin oluşturun. |
| Telemetry görünmüyor | Dashboard'dan bir işlem üretin, background publish için kısa süre bekleyin, sonra yenileyin. `docker compose logs orders-api api` çıktısını inceleyin. |
| Backend kodu güncel görünmüyor | `docker compose up -d --build api worker beat` çalıştırın. |
| Bir port kullanımda | Çakışan process'i durdurun veya `docker-compose.yml` içindeki host-side portu değiştirin. |
| Yerel veri tutarsız | Tam sıfırlamayı bilinçli olarak istiyorsanız `docker compose down -v` kullanın. |

## Proje yapısı

- `backend/` — Django REST API, authentication, telemetry persistence, Celery task'ları ve ML feature materialization.
- `frontend/` — Vue 3 + TypeScript operator dashboard.
- `demo-services/` — bağımsız container'larda çalışan demo application'lar ve worker'ları.
- `telemetry/` — OpenTelemetry Collector configuration.
- `docs/` — operator, data collection ve ML feature-pipeline dokümantasyonu.
- `specs/` — AI-assisted development kayıtları, design decision'lar ve test evidence.

## Mevcut ve sonraki kapsam

Tamamlananlar: gerçek service workflow, service dashboard, System Overview, raw retention ve `features.v1` materialization.

Sonraki adımlar: Isolation Forest training/scoring, anomaly kayıtları, controlled-fault ground truth, incident correlation, external benchmark dataset'leri ve redacted external LLM analysis API.

## Contribution workflow

Repository üzerinde değişiklik yapmadan önce `AGENTS.md` dosyasını okuyun. Kapsamlı değişikliklerde [`specs/README.md`](specs/README.md) içindeki spec lifecycle kullanılır: `draft → active → verified → done/archive`.

`feature/<name>` veya `fix/<name>` branch formatını kullanın. Değişiklikler pull request üzerinden merge edilir; source branch merge sonrasında silinmelidir.
