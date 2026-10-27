# AVATAR Yapay Zekâ Yarışması — Üretim, Maliyet, Satış ve Lot İzlenebilirliği

Bir gıda işletmesinde hammaddenin alışından nihai satışına kadar stok hareketlerini, gerçek maliyeti ve lot izlenebilirliğini yöneten sistem: merkezi sunucu ve MySQL, web yönetim/raporlama arayüzü, Kotlin Android satış uygulaması (yerelde SQLite) ve iki yapay zekâ modeli (üretim verimi/EKP tahmini, parçalama verimi tahmini).

> **Durum (28 Ekim 2026):** Bütün şartname maddeleri uygulandı ve sınandı; sistem gerçek bir işletmede kullanılacak biçimde genişletildi. Sunucu, web ve Android'de çalışan parçalar:
>
> - **Görev 1:** fason (dış) üretim, birim maliyet (EKP) 18,16 €.
> - **Görev 2:** parçalama, kuruşu kuruşuna maliyet dağıtımı, Kotlin ile lot bazlı satış.
> - **Görev 3:** ileri/geri izleme, geri çağırma, market listesi ve CSV, müşterinin dağıttığı yerler, iade, fire, yeniden işleme.
> - **İki yapay zekâ modeli**, yedi rapor.
> - **Gerçek kullanım:** rollere göre ekranlar (yönetici, depo, üretim, kalite, mağaza, satış), kullanıcı ve şifre yönetimi, mağaza satışı (ödeme türüyle), gün sonu, depo/araç sayımı, son kullanma takibi ve kuralı (ilk dolan ilk çıkar), kritik stok uyarısı, geri çağırma tatbikatı, yazdırılabilir belgeler (barkodlu lot etiketi, fiş/irsaliye, geri çağırma bildirimi, gün sonu, sayım tutanağı).
> - **Sade, iki dilli arayüz:** web ve telefon Türkçe / English; terimler sadeleştirildi.
>
> Testler: 215 sunucu, 4 yapay zekâ, 26 web, 22 Android ve **23 kabul testi** (AT-01…AT-15). Kalan teslim adımları: video, GitHub'a yükleme, e-posta ([docs/submission_checklist.md](docs/submission_checklist.md)).
>
> **Takım:** Synera · **Yığın:** Python + FastAPI (sunucu ve YZ), MySQL 8.4, React + Vite + TypeScript (web), Kotlin + Compose + Room (Android), Docker Compose — bkz. [docs/technical_research.md](docs/technical_research.md)

**Ekran görüntüleri:** Sistemi kurmadan bütün ekranları görmek için [docs/ekran_goruntuleri](docs/ekran_goruntuleri/README.md) (58 görüntü: web ve Android, yeni arayüz).

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
| 11 | Görev 1 API ve web (T-09, T-10) | Tamamlandı — URT-2026-045 senaryosu arayüzden yürüyor |
| 12 | Görev 2 API ve web (T-11, T-12) | Tamamlandı — şartname dağıtım rakamları birebir |
| 13 | Android satış ve gönderim (T-14, T-15) | Tamamlandı — çevrimdışı satış, tekrar güvenli gönderim |
| 14 | Görev 3 API ve web (T-16, T-17), iade, fire, ters kayıt, demo profili | Tamamlandı — ET-2026-001 → Market A 30 / B 25 / C 30 kurulumdan sonra hazır |
| 15 | Yapay zekâ (T-18…T-21) ve değerlendirme raporu | Tamamlandı — iki model de referans yöntemden iyi |
| 16 | Raporlar (T-22) ve web/Android arayüzü | Tamamlandı — 28 Ekim'de sade tasarımla yeniden yapıldı |
| 17 | Kabul testleri (T-23), yeniden işleme, temiz kurulum provası | Tamamlandı — 23/23 kabul testi |
| 18 | Denetim düzeltmeleri, gerçek kullanım özellikleri, yeni arayüz, dil seçeneği | Tamamlandı — 28 Ekim |
| 19 | Video, GitHub, e-posta (T-27, T-28) | 31 Ekim – 1 Kasım |

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
| `docs/is_bolumu.md` | İki kişilik iş bölümü: gereksinim kapsamı, kim neyin sahibi, takvim, birlikte çalışma |
| `docs/ekran_goruntuleri/` | Uygulamanın bütün ekranları (web ve Android), açıklamalı galeri |
| `docs/senkronizasyon.md` | SQLite ↔ MySQL senkronizasyonu: veriler nasıl tutarlı kalır |
| `reports/ai_degerlendirme.md` | Yapay zekâ değerlendirmesi: yöntem, veri, referansla karşılaştırma, hata, sınırlılıklar |
| `reports/gorev2_tutarsizliklar.md` | Görev 2 örnek görselindeki iki tutarsızlık ve çözümümüz |
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

**8000 ya da 8080 portu başka bir uygulamada kullanılıyorsa** `.env` içinde `API_PORT` ve `WEB_PORT` değiştirilir (ör. 18000 ve 18080); adresler de buna göre değişir.

İlk açılışta veritabanı şeması kurulur ve boş veritabanına **demo profili** yüklenir (`SEED_PROFILE=demo`). Ana veriler ve hammadde alışları `data/seed/base.json`'dan gelir. Üstüne şartnamenin zorunlu senaryosu uygulamanın kendi servisleriyle yazılır (`backend/app/demo.py`):

- URT-2026-045: ET-2026-001 + baharat + bağırsak → SUC-2026-045, 85 paket, EKP 18,16 €.
- SUC-2026-045 araca yüklenir ve Android kanalından satılır: Market A 30, Market B 25, Market C 30 paket.
- Market B'nin şubelerine dağıtımı kayıtlıdır (15 + 10).
- Görev 2 için KUZU-2026-012'den örnek parçalama yapılır.

Yalnız ana verileri istiyorsanız `.env` içinde `SEED_PROFILE=base` yapın. Bütün firma ve kişi adları uydurmadır.

| Demo kullanıcısı | Şifre | Rol | Ne görür |
|---|---|---|---|
| `yonetici` | `yonetici123` | Yönetici | Bütün ekranlar, kullanıcılar, ürün ve fiyatlar |
| `depo1` | `depo1234` | Depo sorumlusu | Mal kabul, stok, son kullanma, sayım, araca yükleme |
| `uretim1` | `uretim123` | Üretim sorumlusu | Fason üretim, parçalama, yeniden işleme, yapay zekâ |
| `kalite1` | `kalite123` | Kalite sorumlusu | Lot izleme, geri çağırma, tatbikat, uyarılar |
| `magaza1` | `magaza123` | Mağaza / kasa | Mağaza satışı, iade, gün sonu |
| `satis1` | `satis123` | Satış elemanı | Yalnız telefon uygulaması (araç ARAC-01) |

Bu şifreler yalnız yerel demo içindir. Yönetici **Kullanıcılar** ekranından yeni hesap açar; yeni hesap ve sıfırlanan şifre geçicidir, kullanıcı ilk girişte kendi şifresini belirler. Hatalı girişler sınırlıdır (5 dakikada 10 deneme).

**Dil:** Web'de üst çubuktaki **TR / EN** seçimi, telefonda sağ üstteki menü. Seçim hatırlanır.

### Şartname senaryosunu 5 dakikada denemek

1. Web'e `yonetici` ile girin. Ana sayfa o günün işlerini gösterir (dolmak üzere lotlar, uyarılar, bekleyen belgeler).
2. **Kalite → Lot izleme → "ET-2026-001 · İleri izle":** zincir ve etkilenen marketler (A 30 / B 25 / C 30), iletişim bilgileri ve müşterinin dağıttığı yerler.
3. **"Geri çağırma başlat"** → neden yazın. ET-2026-001 ve SUC-2026-045 tek işlemde satışa kapanır, liste hemen çıkar. **"İletişim listesi (CSV)"** ve **"Yazdır"** (müşteri başına geri çağırma bildirimi).
4. **"SUC-2026-045 · Geri izle":** üç hammadde lotu, tedarikçiler, URT-2026-045.
5. **Üretim → Fason üretim → URT-2026-045:** birim maliyet (EKP) dökümü (1.543,50 € / 85 = 18,16 €), kâr, marj ve yapay zekâ kartında tahmin–gerçek–sapma.
6. **Üretim → Parçalama → PRC-2026-012:** ağırlık dengesi (25 = 22 + 3 fire) ve 351,00 €'nun kuruşu kuruşuna dağıtımı.
7. **Satış → Mağaza satışı** (`magaza1` ile de olur): ürün ekleyin, lot kendiliğinden seçilir; ödeme türünü seçip kaydedin, fişi yazdırın. **Gün sonu** ödeme türüne göre toplamları verir.
8. **Raporlar** (yedi rapor, CSV) ve **Yapay zekâ tahminleri** (referansla karşılaştırma).
9. Android'de `satis1` ile girip eşitleyin. Satış dört adımdır (müşteri → ürün → ödeme → özet); geri çağrılan ve süresi geçen lot satılamaz. **Gün sonu** sekmesinde günün özeti ve araç sayımı.

Durdurmak için `docker compose down`; veritabanını da silmek için `docker compose down -v`.

### Testler

```bash
docker compose run --rm --no-deps api pytest -v
```

Testler ayrı bir `avatar_test` veritabanında çalışır ve demo verisine dokunmaz.

```bash
docker compose run --rm --no-deps api sh -c "ruff check . && ruff format --check ."
```

Yapay zekâ paketinin testleri:

```bash
docker compose run --rm --no-deps api sh -c "cd /ml && pytest -q"
```

**Kabul testleri (AT-01…AT-15):** Betik sistemi ayrı bir kopyada sıfırdan kurar, şartname senaryolarını çalışan sisteme gerçek HTTP istekleriyle sınar ve kopyayı siler. Açık sisteme ve verisine dokunmaz.

```bash
sh scripts/kabul_testleri.sh
```

Son çalıştırma sonuçları:
- [reports/test_results.md](reports/test_results.md)
- [reports/kabul_testleri.md](reports/kabul_testleri.md): 23/23; ET-2026-001 izlemesi 0,041 sn (28 Ekim).

### Web arayüzünü geliştirme modunda çalıştırma

API Docker'da çalışırken, `web/` klasöründe:

```bash
npm install
```

```bash
npm run dev
```

Arayüz http://localhost:5173 adresinde açılır; `/api` istekleri yerel API'ye yönlendirilir (port `API_PORT` ortam değişkeninden, yoksa 8000).

API değişince web tiplerini yenilemek için (API çalışırken, depo kökünden): `sh scripts/api_tipleri_yenile.sh`.

Web birim testleri: `web/` klasöründe `npm test`.

### Android uygulaması

Hazır APK: GitHub deposunun **Releases** bölümünde (`AVATAR_Synera.apk`). Derleme, emülatörde çalıştırma ve Android 17 yerel ağ izni notu: [android/README.md](android/README.md). Kısaca: `android/` klasöründe `./gradlew assembleDebug testDebugUnitTest`; emülatörde sunucu adresi `http://10.0.2.2:8000` (API portu değiştiyse o port), kullanıcı `satis1` / `satis123`.

### Bilinen sınırlamalar

- **Yapay zekâ verisi sentetiktir.** Modellerin referansa göre başarısı, gerçek işletmede aynı başarının kanıtı değildir. Model B'de omuz payında model referanstan biraz kötüdür ([reports/ai_degerlendirme.md](reports/ai_degerlendirme.md) §7).
- **Görev 2'nin "örnek görseli" şartname PDF'inde yoktur.** Tutarsızlıklar metindeki rakamlarla açıklandı ([reports/gorev2_tutarsizliklar.md](reports/gorev2_tutarsizliklar.md)).
- **Fiş/irsaliye mali belge değildir.** e-Fatura/e-Arşiv ve yazar kasa entegrasyonu yoktur; belgelerdeki işletme adı `web/src/pages/PrintPage.tsx` içinde sabittir.
- **Sunucunun hata ayrıntıları Türkçedir.** İngilizce ekranda önce hatanın türü İngilizce, ardından sunucunun Türkçe açıklaması görünür.
- **Sayımda fazla çıkan mal stoka eklenmez;** kaynağı araştırılıp ilgili belge düzeltilmelidir (eksik çıkan mal fire olarak düşülür).
- **İsteğe bağlı yapay zekâ özellikleri** (fatura okuma, anomali uyarıları) kapsam dışıdır. Geri çağırma ihlali uyarısı kural tabanlıdır.
- **Tek ana depo** varsayılır. Dış üretici ve araç depoları ayrıca tanımlanır.
- **Şifreler yalnız yerel demo içindir.** Gerçek kullanımda `.env` ile değiştirilmeli ve HTTPS arkasında çalıştırılmalıdır. Hatalı giriş sınırı sunucu belleğinde tutulur (tek sunucu süreci için).

### Sorun giderme

- **Windows'ta Docker Desktop açılırken "initializing Secrets Engine … engine.sock … The file cannot be accessed by the system" hatası verip kapanıyorsa:** Önceki oturumdan kalmış bir soket dosyası açılışı engelliyor. Docker Desktop kapalıyken `%LOCALAPPDATA%\docker-secrets-engine` klasörünü yeniden adlandırıp Docker Desktop'ı tekrar açın. "Reset to factory defaults" seçeneği bütün imaj ve verileri sildiği için önerilmez.

## Değişiklik geçmişi

[CHANGELOG.md](CHANGELOG.md)
