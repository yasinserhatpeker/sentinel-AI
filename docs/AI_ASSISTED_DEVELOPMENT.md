# AI destekli geliştirme

SentinelAI, spec tabanlı ve kontrollü bir AI destekli geliştirme akışı kullanır.

## Benimsenen yapı

- `AGENTS.md` ve `CLAUDE.md` agent’ları görev bazlı kurallara yönlendirir.
- `specs/` gereksinimleri, mimari kararları ve görevleri birlikte tutar.
- Kapsamlı API, model, analiz, route, ortak service ve deployment değişikliklerinden önce spec açılır.
- Spec’lerde kabul kriterleri, doğrulama etiketleri, açık sorular ve karar günlüğü bulunur.
- Backend ve frontend kuralları, implementation pattern’leri incelenmeden önce okunur.
- Secret, production payload ve hassas log’lar kaynak koduna veya spec’lere yazılmaz.

## SentinelAI sınırları

- Scope; environment, service, deployment ve time range üzerinden ifade edilir.
- Authentication ve authorization kararları spec’lerde açıkça kaydedilir.
- Detection ve incident correlation evidence reference ve tekrarlanabilir configuration tutar.
- LLM çıktısı bounded, redacted ve advisory’dir; doğrudan operasyonel aksiyon çalıştıramaz.
- Fault injection yalnızca demo/test ortamında ve açık opt-in ile çalışır.

## Çalışma sırası

1. `AGENTS.md`, ilgili `.ai/` dosyaları ve aktif spec okunur.
2. Değişiklikten önce mevcut implementation incelenir.
3. Contract ve mimari değişiklikler spec’e yazılır.
4. Kabul kriterlerini karşılayan en küçük değişiklik uygulanır.
5. `tasks.md` içinde belirtilen doğrulamalar çalıştırılır.
6. Commit öncesi diff ve commit mesajı kullanıcıya gösterilir.
