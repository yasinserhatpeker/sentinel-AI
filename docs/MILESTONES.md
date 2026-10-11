# SentinelAI milestone’ları

Aşağıdaki tarihler ve teslimatlar proje raporundan çıkarılmıştır. Bunlar proje gereksinimleridir;
agent talimatlarının yerine geçmez.

| Tarih | Milestone | Teslimat |
|---|---|---|
| 15.10.2026 | Araştırma, gereksinim analizi ve sistem tasarımı | Kapsam, veri akışı, telemetry modeli, mimari sınırlar, minimum metric seti ve fault-injection senaryoları |
| 29.10.2026 | Telemetry altyapısı, demo sistem ve dashboard temeli | Demo uygulaması, HTTP/queue/runtime/database toplama, ingestion API, aggregation ve ilk Vue dashboard’u |
| 12.11.2026 | Anomaly detection ve fault-injection deneyleri | Threshold/statistical baseline, Isolation Forest, kontrollü fault’lar ve precision/recall/F1/false-positive/delay sonuçları |
| 03.12.2026 | Incident correlation ve AI destekli kök neden analizi | Zaman/service correlation, incident timeline, structured context, hypothesis, evidence ve inceleme adımları |
| 24.12.2026 | Entegrasyon, test, başarı analizi ve final sunumu | Uçtan uca entegrasyon, scenario tabanlı değerlendirme, limitler, demo, teknik dokümantasyon ve sonuç tabloları |

## Uygulama sırası

Sıra bağımlılıkları izler: önce contract’lar tanımlanır, sonra telemetry toplanır ve
aggregate edilir, ardından anomaly detection yapılır, incident’lar ilişkilendirilir ve
en son LLM destekli açıklama ile final değerlendirme eklenir.
