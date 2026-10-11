---
slug: research-system-design
title: Araştırma, gereksinim analizi ve sistem tasarımı
author: Yasin Serhat Peker
area: platform
status: active
created: 2026-10-11 17:05
updated: 2026-10-11 17:05
---

# Faz 1 — tasarım teslimi

- [x] Proje raporundan 15 Ekim milestone’u çıkarıldı.
- [x] Observability sinyalleri, semantic convention’lar ve incident-management yaklaşımı araştırıldı.
- [x] Birincil kaynaklar kaydedildi ve bulgular SentinelAI kararlarına çevrildi.
- [x] Kapsam, kapsam dışı alanlar ve ilk demo akışı tanımlandı.
- [x] Telemetry envelope, dimension’lar ve minimum metric seti tanımlandı.
- [x] Mimari bileşenler ve synchronous/asynchronous sınırlar tanımlandı.
- [x] Anomaly, incident ve AI-analysis result sınırları tanımlandı.
- [x] Fault-injection senaryoları ve değerlendirme metrikleri tanımlandı.
- [x] Fault injection’ın yalnızca demo/test ortamında çalışmasını sağlayan önlemler tanımlandı.
- [x] 29 Ekim milestone’u için implementation riskleri ve kararları kaydedildi.

# Faz 2 — doğrulama

Doküman doğrulaması 11.10.2026 tarihinde proje raporu, araştırma kaynakları ve ortaya
çıkan requirements/design belgeleri incelenerek tamamlandı. Bu milestone production kodu
üretmediği için uygulama komutu çalıştırılması gerekmemektedir.

# Faz 3 — sonraki milestone handoff’u

- [ ] Demo service ve telemetry ingestion API geliştir.
- [ ] PostgreSQL telemetry/aggregate modellerini ve Celery aggregation işlerini ekle.
- [ ] System status ve metric grafiklerini gösteren ilk Vue dashboard’u oluştur.
- [ ] Contract testleri ve tekrarlanabilir local Docker demo’su ekle.
