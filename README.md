# AVATAR Yapay Zekâ Yarışması — Üretim, Maliyet, Satış ve Lot İzlenebilirliği

Bir gıda işletmesinde hammaddenin alışından nihai satışına kadar stok hareketlerini, gerçek maliyeti ve lot izlenebilirliğini yöneten sistem: merkezi sunucu ve MySQL, web yönetim/raporlama arayüzü, Kotlin Android satış uygulaması (yerelde SQLite) ve iki yapay zekâ modeli (üretim verimi/EKP tahmini, parçalama verimi tahmini).

> **Durum (24 Ekim 2026):** Çekirdek hazır: veritabanı, stok defteri, lot ağı, maliyet motoru; giriş ve Android'e veri çekme uçları. Android uygulamasının iskeleti emülatörde çalışıyor (giriş, eşitleme, araç stoku). İş ekranları (dış üretim, parçalama, satış, geri çağırma) henüz yok.
>
> **Takım:** Synera · **Yığın:** Python + FastAPI (sunucu ve YZ), MySQL 8.4, React + Vite + TypeScript (web), Kotlin + Compose + Room (Android), Docker Compose — bkz. [docs/technical_research.md](docs/technical_research.md)

## Önemli tarihler

| Tarih | Olay |
|---|---|
| 31 Ekim 2026 akşam | Kod dondurma, demo videosu |
| **1 Kasım 2026 23:59** | Son teslim (GitHub bağlantısı + ≤ 15 dk video) |

## Aşamalar

| # | Aşama | Durum |
|---|---|---|
| 1 | Proje analizi | v0.2 — ekip cevapları işlendi, birkaç soru açık |
| 2 | Proje klasörü | Hazır |
| 3 | Gereksinimler | v0.1 taslak |
| 4 | Teknik araştırma ve teknoloji seçimi | Tamamlandı — ADR-001…007 kabul edildi |
| 5 | Mimari | v0.1 onaylandı (mimari, veri modeli, API, ADR-001…008) |
| 6 | Geliştirme planı | v0.1 |
| 7 | Ortam kurulumu (T-05) | Tamamlandı — sunucu, web, MySQL, Android Studio, SDK, emülatör |
| 8 | Veritabanı şeması (T-06) | Tamamlandı — 31 tablo, defter tetikleyicileri, örnek ana veriler |
| 9 | Stok defteri, lot ağı, maliyet motoru (T-07, T-08) | Tamamlandı — şartname rakamları testlerle doğrulandı |
| 10 | Android iskeleti (T-13) | Tamamlandı — giriş, eşitleme, araç stoku; emülatörde uçtan uca denendi |
| 11+ | Görev ekranları ve API'leri, Android satış, YZ, raporlar, teslim | Başlanmadı |

Ayrıntılı iş listesi ve günlük durum: [docs/development_plan.md](docs/development_plan.md).

## Klasör yapısı

| Yol | Amaç |
|---|---|
| `docs/project_analysis.md` | Şartnamenin madde madde analizi, strateji, sorular, riskler |
| `docs/requirements.md` | Kimlikli gereksinimler (FR / NFR / TR / CR / CON / AS) |
| `docs/technical_research.md` | Teknoloji karşılaştırmaları (Aşama 4) |
| `docs/architecture.md` | Mimari: bileşenler, iş kuralları, akışlar, senkronizasyon, YZ bağlantısı, güvenlik, çalıştırma |
| `docs/data_model.md` | Veri modeli: ER diyagramı, tablolar, hareket türleri, değişmezler, Android yerel tabloları |
| `docs/api.md` | API sözleşmesi: uç noktalar, hata kodları, örnek istek/yanıtlar |
| `docs/development_plan.md` | İş listesi, takvim, durum günlüğü |
| `docs/testing_strategy.md` | Test seviyeleri, şartname kabul testleri, gereksinim–test eşlemesi |
| `docs/submission_checklist.md` | Teslim kontrol listesi |
| `docs/decisions/` | Karar kayıtları (ADR) |
| `backend/` | Merkezi sunucu ve REST API |
| `web/` | Web yönetim ve raporlama arayüzü |
| `android/` | Kotlin Android satış/operasyon uygulaması |
| `ml/` | Yapay zekâ modelleri, değerlendirme ve tahmin servisi |
| `data/seed/` | Demo ve testler için örnek kayıtlar |
| `data/synthetic/` | YZ için üretilmiş örnek veri ve varsayımları |
| `tests/` | Bileşenler arası uçtan uca / kabul testleri |
| `scripts/` | Kurulum, örnek veri yükleme vb. yardımcı betikler |
| `reports/` | Test sonuçları, YZ değerlendirme raporları; `design_validation/` tasarım doğrulama betiği ve çıktısı |
| `_kaynak/` | Yarışma belgeleri — **depoya gönderilmez** |

## Kurulum ve çalıştırma

### Gerekenler

- Docker (Windows/macOS'ta Docker Desktop; Windows'ta WSL2 ile)
- Web arayüzünü Docker dışında geliştirmek için: Node.js 22
- Android uygulamasını derlemek için: Android Studio (kendi JDK'si yeterli) ve Android SDK 37

### Tek komutla çalıştırma

```bash
docker compose up --build -d
```

| Adres | Ne |
|---|---|
| http://localhost:8080 | Web arayüzü |
| http://localhost:8000/docs | API belgesi (OpenAPI, deneme arayüzü) |
| http://localhost:8000/api/v1/health | Servis ve veritabanı durumu |

Parolaların varsayılan değerleri yalnız yerel kullanım içindir. Değiştirmek için `.env.example` dosyasını `.env` adıyla kopyalayıp düzenleyin.

İlk açılışta veritabanı şeması kurulur ve boş veritabanına örnek kayıtlar (`data/seed/base.json`) yüklenir: ana veriler ve şartname senaryosunun hammadde lotları (ET-2026-001 vb.). Bütün firma ve kişi adları uydurmadır.

| Demo kullanıcısı | Parola | Rol |
|---|---|---|
| `yonetici` | `yonetici123` | Yönetici (web) |
| `satis1` | `satis123` | Satış elemanı (Android, araç deposu ARAC-01) |

Bu parolalar yalnız yerel demo içindir.

Durdurmak için `docker compose down`; veritabanını da silmek için `docker compose down -v`.

### Testler

```bash
docker compose run --rm --no-deps api pytest -v
```

Testler ayrı bir `avatar_test` veritabanında çalışır ve demo verisine dokunmaz.

```bash
docker compose run --rm --no-deps api sh -c "ruff check . && ruff format --check ."
```

Son çalıştırma sonuçları: [reports/test_results.md](reports/test_results.md).

### Web arayüzünü geliştirme modunda çalıştırma

API Docker'da çalışırken, `web/` klasöründe:

```bash
npm install
```

```bash
npm run dev
```

Arayüz http://localhost:5173 adresinde açılır; `/api` istekleri yerel API'ye (8000) yönlendirilir.

### Android uygulaması

Derleme, emülatörde çalıştırma ve Android 17 yerel ağ izni notu: [android/README.md](android/README.md). Kısaca: `android/` klasöründe `./gradlew assembleDebug testDebugUnitTest`; emülatörde sunucu adresi `http://10.0.2.2:8000`, kullanıcı `satis1` / `satis123`.

### Sorun giderme

- **Windows'ta Docker Desktop açılırken "initializing Secrets Engine … engine.sock … The file cannot be accessed by the system" hatası verip kapanıyorsa:** Önceki oturumdan kalmış bir soket dosyası açılışı engelliyor. Docker Desktop kapalıyken `%LOCALAPPDATA%\docker-secrets-engine` klasörünü yeniden adlandırıp Docker Desktop'ı tekrar açın. "Reset to factory defaults" seçeneği bütün imaj ve verileri sildiği için önerilmez.

## Değişiklik geçmişi

[CHANGELOG.md](CHANGELOG.md)
