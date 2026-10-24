# ADR-002: Web arayüzü React + Vite + TypeScript + Ant Design

- Durum: **Kabul edildi** (ekip onayı: 24.10.2026)
- Tarih: 24.10.2026
- İlgili gereksinimler: TR-005, FR-1xx–3xx ekranları, FR-601–606
- Ayrıntı: `docs/technical_research.md` §3 (D-02)

## Bağlam
Yönetim ve raporlama ekranları çoğunlukla tablo ve formdan oluşuyor. Şartname React'i öneriyor.

## Seçenekler
1. **React + Vite (tek sayfa uygulaması) + TypeScript + Ant Design + TanStack Query + openapi-typescript**
2. Next.js — sunucu tarafı çizim gereksiz; ek karmaşıklık.
3. Sunucuda üretilen sayfalar (Jinja + htmx) — en az kod; ama değerlendirici büyük olasılıkla React bekliyor.
4. Bileşen kütüphanesi olarak Mantine — daha hafif, tablo özellikleri daha sınırlı.

## Karar
Seçenek 1. API tipleri FastAPI'nin OpenAPI tanımından üretilir; sözleşme bozulursa web kodu derlenirken hata verir. Ekipte TypeScript bilen yoksa aynı yığın JavaScript ile kullanılır.

## Sonuçlar
- Tablo, form ve tarih seçici hazır gelir; Türkçe dil paketi var.
- Ayrı bir derleme adımı ve Node.js gerekir; Docker imajında derlenir.

## Uygulama notları (T-10)
- openapi-typescript 7.13.0 yalnız TypeScript 5'i eş bağımlılık olarak kabul ediyor; projede TypeScript 6 var. Bu yüzden üretici bağımlılık olarak eklenmedi, `npm run api:types` ile `npx` üzerinden kendi ortamında çalışıyor. Üretilen `src/api/schema.d.ts` depoya giriyor; Docker derlemesi üreticiye ihtiyaç duymuyor.
- Yönlendirme için kütüphane eklenmedi: 13 sayfa için History API + `useSyncExternalStore` ile 40 satırlık bir yönlendirici yeterli (`lib/router.ts`). Derin bağlantılar nginx'te `index.html`'e düşüyor.
- Para ve miktar ekranda da kayan noktalı sayıya çevrilmiyor: ön izleme hesapları `BigInt` ile ölçeklenmiş tamsayıyla, sunucudaki gibi yarım yukarı yuvarlanarak yapılıyor (`lib/decimal.ts`, ADR-006).
- Derlenen paket 1,2 MB (sıkıştırılmış ≈ 378 kB); büyük kısmı Ant Design. Yerel ağdaki bir yönetim arayüzü için kabul edildi; gerekirse sayfalar tembel yüklemeyle bölünebilir.
