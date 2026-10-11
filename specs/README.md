# specs/ — SentinelAI

Spec’ler, SentinelAI’deki kapsamlı işler için kısa Türkçe kayıtlardır. Her aktif spec
`requirements.md`, `design.md` ve `tasks.md` dosyalarından oluşur.

API, event schema, data model, detector, correlation rule, LLM context contract, route,
shared service/store, deployment configuration veya CI davranışı değişmeden önce spec açılır.
Küçük ve izole UI, metin, yorum veya dokümantasyon değişiklikleri spec gerektirmeyebilir.

## Gerekli çalışma akışı

1. İlgili root ve `.ai/` kurallarını oku.
2. Gereksinimleri yazmadan önce mevcut kodu incele.
3. Kapsamı, kabul kriterlerini, mimari kararları, riskleri ve açık soruları kaydet.
4. Owner onayına kadar `status: draft` durumunu koru.
5. Yalnızca spec aktif olduktan sonra uygulama yap.
6. Listelenen doğrulamaları çalıştır ve sonuçları `tasks.md` içine yaz.

Üç dosyada `slug`, `title`, `author`, `area`, `status`, `created` ve `updated` bulunur.
Requirements ayrıca `branches` ve `verification` taşır. Bekleyen kriter için `- [ ]`,
doğrulanan kriter için `- [x]`, yalnızca gerekçesi yazılmış manuel kriter için `- [~]`
kullanılır. `INDEX.md` append-only’dir. Tamamlanan spec’ler `specs/archive/YYYY-MM-DD-slug/`
altına taşınır. Spec içine credential, token, production payload veya secret yazılmaz.
