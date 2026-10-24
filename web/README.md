# web/

Web yönetim ve raporlama arayüzü: hammadde/lot kayıtları, dış üretim emri, parçalama, izlenebilirlik ve geri çağırma ekranları, raporlar, yapay zekâ tahminlerinin gösterimi.

**Teknoloji:** React 19 + Vite 8 + TypeScript (strict) + Ant Design 6 (Türkçe dil paketi) + TanStack Query (`docs/decisions/ADR-002`). Kod denetimi: oxlint.

**Durum (T-10):** Görev 1 ekranları hazır: giriş/çıkış, ana sayfa (sistem durumu, hızlı işlemler), ürün ve cari kartları, hammadde alışı, stok durumu, lotlar ve lot ayrıntısı (hareket geçmişi, lot ağı), transferler (araca yükleme), dış üretim emirleri (oluştur, sevk, kabul, EKP dökümü). Web yalnız yönetici hesabına açıktır. Parçalama, izleme/geri çağırma, raporlar ve yapay zekâ ekranları sonraki işlerde eklenecek.

| Dosya | Amaç |
|---|---|
| `src/main.tsx` | Uygulama kökü: Türkçe antd ayarı, sorgu istemcisi, oturum |
| `src/App.tsx` | Sayfa düzeni (menü, üst çubuk) ve yol tablosu |
| `src/api/schema.d.ts` | OpenAPI tanımından üretilen tipler (`npm run api:types`; elle düzenlenmez) |
| `src/api/client.ts` | İstek, belirteç, Türkçe hata mesajı; 401'de girişe dönüş |
| `src/auth/` | Oturum bağlamı, giriş ve çıkış |
| `src/pages/` | Ekranlar |
| `src/components/` | Ortak parçalar: sayfa çerçevesi, pencere formu, durum etiketleri, bağlantı |
| `src/lib/` | Ondalık hesap (BigInt), Türkçe biçimler, yönlendirici, form kuralları, etiketler |
| `vite.config.ts` | Geliştirmede `/api` → `http://localhost:8000` yönlendirmesi |
| `nginx.conf` | Docker'da statik dosyalar + `/api` ters vekili |

Komutlar: `npm run dev` (geliştirme), `npm run build` (tip denetimi + derleme), `npm run lint` (oxlint), `npm test` (Vitest birim testleri), `npm run api:types` (API tiplerini `../docs/openapi.json`'dan yeniden üretir).

İlgili gereksinimler: `docs/requirements.md` → FR-1xx, FR-2xx, FR-3xx, FR-5xx, FR-6xx, TR-005.
