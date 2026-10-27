# web/

Web yönetim ve raporlama arayüzü: hammadde/lot kayıtları, dış üretim emri, parçalama, izlenebilirlik ve geri çağırma ekranları, raporlar, yapay zekâ tahminlerinin gösterimi.

**Teknoloji:** React 19 + Vite 8 + TypeScript (strict) + Ant Design 6 (+ kendi simge paketi `@ant-design/icons`, antd ile zaten gelir) + TanStack Query (`docs/decisions/ADR-002`). Kod denetimi: oxlint.

**Durum (28 Ekim):** Sade tasarım, işe göre menü; her rol yalnız kendi ekranlarını görür (yönetici, depo, üretim, kalite, mağaza — satış elemanı telefon kullanır). Ekranlar: rol bazlı ana sayfa, mağaza satışı, satışlar ve iadeler, gün sonu, mal kabul, stok, son kullanma takibi, sayım, araca yükleme, lotlar, fason üretim, parçalama, yeniden işleme, reçeteler, lot izleme, geri çağırma, tatbikat, uyarılar, raporlar, yapay zekâ, kullanıcılar, ürünler, firmalar, şifre değiştirme; yazdırılabilir belgeler (`/yazdir/...`). Türkçe / English.

| Dosya | Amaç |
|---|---|
| `src/main.tsx` | Uygulama kökü: Türkçe antd ayarı, sorgu istemcisi, oturum |
| `src/App.tsx` | Sayfa düzeni (menü, üst çubuk) ve yol tablosu |
| `src/api/schema.d.ts` | OpenAPI tanımından üretilen tipler (`npm run api:types`; elle düzenlenmez) |
| `src/api/client.ts` | İstek, belirteç, Türkçe hata mesajı; 401'de girişe dönüş |
| `src/auth/` | Oturum bağlamı, giriş ve çıkış |
| `src/pages/` | Ekranlar |
| `src/components/` | Ortak parçalar: sayfa çerçevesi, pencere formu, durum etiketleri, bağlantı |
| `src/lib/` | Ondalık hesap (BigInt), dile göre biçimler, yönlendirici, form kuralları, etiketler, roller (`roles.ts`), ilk dolan ilk çıkar (`fefo.ts`), Code 128 barkod (`code128.ts`), dil (`i18n.ts`) |
| `src/i18n/en.ts` | İngilizce sözlük; anahtar ekrandaki Türkçe metin. Yeni metin eklenince `npm test` çevirisi eksikse uyarır |
| `src/pages/PrintPage.tsx` | Yazdırılabilir belgeler: lot etiketi, fiş/irsaliye, geri çağırma bildirimi, gün sonu, sayım tutanağı, tatbikat raporu |
| `vite.config.ts` | Geliştirmede `/api` → `http://localhost:8000` yönlendirmesi |
| `nginx.conf` | Docker'da statik dosyalar + `/api` ters vekili; güvenlik başlıkları (CSP vb.), sıkıştırma, gerçek istemci adresi |

Komutlar: `npm run dev` (geliştirme), `npm run build` (tip denetimi + derleme), `npm run lint` (oxlint), `npm test` (Vitest birim testleri), `npm run api:types` (API tiplerini `../docs/openapi.json`'dan yeniden üretir).

İlgili gereksinimler: `docs/requirements.md` → FR-1xx, FR-2xx, FR-3xx, FR-5xx, FR-6xx, TR-005.
