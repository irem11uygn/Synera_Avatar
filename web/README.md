# web/

Web yönetim ve raporlama arayüzü: hammadde/lot kayıtları, dış üretim emri, parçalama, izlenebilirlik ve geri çağırma ekranları, raporlar, yapay zekâ tahminlerinin gösterimi.

**Teknoloji:** React 19 + Vite 8 + TypeScript (strict) + Ant Design 6 (Türkçe dil paketi) + TanStack Query (`docs/decisions/ADR-002`). Kod denetimi: oxlint.

**Durum:** İskelet hazır. Tek sayfa: "Sistem durumu" (API ve veritabanı). İş ekranları T-10'dan itibaren eklenecek. API tipleri ileride OpenAPI tanımından üretilecek.

| Dosya | Amaç |
|---|---|
| `src/main.tsx` | Uygulama kökü: Türkçe antd ayarı, sorgu istemcisi |
| `src/App.tsx` | Sayfa düzeni |
| `src/api/` | API çağrıları |
| `vite.config.ts` | Geliştirmede `/api` → `http://localhost:8000` yönlendirmesi |
| `nginx.conf` | Docker'da statik dosyalar + `/api` ters vekili |

Komutlar: `npm run dev` (geliştirme), `npm run build` (tip denetimi + derleme), `npm run lint` (oxlint).

İlgili gereksinimler: `docs/requirements.md` → FR-1xx, FR-2xx, FR-3xx, FR-5xx, FR-6xx, TR-005.
