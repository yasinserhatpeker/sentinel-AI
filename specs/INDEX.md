# Spec Index

**Append-only — bu dosyayı yeniden biçimlendirme.** Spec oluşturulduğunda satır eklenir;
durum değiştiğinde aynı satır güncellenir. Mevcut satırlar taşınmaz. Onarım için
[`README.md`](./README.md) içindeki spec indeks kurallarını kullan.

**Sütunlar:** `slug` kimliği · `title` · işi isteyen insanın `author` adı · `area` ·
`status` (`draft` / `active` / `done`) · `updated` (`DD/MM/YYYY HH:mm`) · `location`.

**Identity** is the slug: active specs live at `specs/<slug>/`, archived ones at
`specs/archive/<YYYY-MM-DD>-<slug>/`.

| slug | title | author | area | status | updated | location |
| --- | --- | --- | --- | --- | --- | --- |
| research-system-design | Araştırma, gereksinim analizi ve sistem tasarımı | Yasin Serhat Peker | platform | active | 11/10/2026 17:05 | specs/research-system-design/ |
