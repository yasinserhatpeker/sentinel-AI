---
slug: research-system-design
title: Araştırma, gereksinim analizi ve sistem tasarımı
author: Yasin Serhat Peker
area: platform
status: active
created: 2026-10-11 17:05
updated: 2026-10-11 17:05
branches: codex/sentinelai-foundation
verification: full
---

# Problem tanımı

SentinelAI için uygulamaya başlamadan önce ortak bir teknik temel gerekir: kapsam,
telemetry sözleşmesi, minimum metric seti, mimari sınırlar ve tekrarlanabilir demo
fault’ları netleşmelidir. Bu kararlar alınmazsa ingestion, detection, correlation ve AI
analizi uyumsuz varsayımlarla gelişir.

# Kabul kriterleri

- [x] Platform hedefi, kapsamı ve kapsam dışı alanları belgelenmiştir. → `manual:doc`
- [x] Uçtan uca telemetry akışı ve service sınırları belgelenmiştir. → `manual:doc`
- [x] HTTP, runtime, database ve queue sinyallerini kapsayan versioned telemetry modeli tanımlanmıştır. → `manual:doc`
- [x] Teknoloji sorumlulukları ve synchronous/asynchronous sınırlar kaydedilmiştir. → `manual:doc`
- [x] High-latency, error-burst, database-slowdown ve queue-backlog senaryoları tanımlanmıştır. → `manual:doc`
- [x] Detection ve sonraki incident-correlation değerlendirme metrikleri tanımlanmıştır. → `manual:doc`
- [x] 29 Ekim milestone’undan önce alınması gereken açık kararlar listelenmiştir. → `manual:doc`

# Açık sorular

15 Ekim tasarım milestone’u için açık soru yoktur. LLM API sağlayıcısının kesin seçimi
sonraki milestone’da yapılacaktır; yerel LLM, fine-tuning ve model hosting kapsam dışıdır.
