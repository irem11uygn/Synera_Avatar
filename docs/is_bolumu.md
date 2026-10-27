# İki Kişilik İş Bölümü ve Kalan İşler

| | |
|---|---|
| Tarih | 27 Ekim 2026 (ikinci sürüm: kulvarlar teknik katmana göre yeniden bölündü) |
| Son teslim | **1 Kasım 2026 23:59** (hedef: 1 Kasım öğleden sonra) |
| Ekip | Kişi 1 — Caner · Kişi 2 — ekip arkadaşı (adı yazılacak) |
| Dayanak | `requirements.md` (gereksinimler), `development_plan.md` (iş listesi T-xx), `api.md` (uç noktalar), `submission_checklist.md` |
| Depo adı | `synera-avatar` (GitHub; teslime kadar gizli, teslimde herkese açık — CR-001) |

Bu belge işleri şartnamenin teknik tablosuna göre iki kulvara böler:

| Şartnamedeki satır | Kulvar |
|---|---|
| Sunucu: Go ya da modern bir teknoloji, REST API (biz Python/FastAPI seçtik) | **Kişi 1** |
| Web: React ya da benzeri | **Kişi 1** |
| Yapay zekâ: uygun bir ML yöntemi + API ile bağlanması | **Kişi 1** |
| Mobil uygulama: Kotlin | **Kişi 2** |
| Yerel veri: SQLite · Merkezi veri ile eşitleme (MySQL) | **Kişi 2** (MySQL şeması sunucu kodunun içinde olduğu için Kişi 1'de kalır) |
| Teslim: kabul testleri, kurulum testi, teslim belgeleri, GitHub, video, e-posta | **Kişi 2** (video ve teslim birlikte) |

Her iş, karşıladığı gereksinim kimlikleriyle ve "bitti" ölçütüyle yazılmıştır. Bir dosyanın tek sahibi olur; sahibi olmayan dosyaya dokunmadan önce diğerine haber verilir.

## 1. Bugünkü durum (27 Ekim)

**Biten işler:** T-01, T-03…T-15 (T-02 açık sorularla sürüyor).

**Çalışanlar:**
- Görev 1 (dış üretim, EKP 18,16 €) ve Görev 2 (parçalama, maliyet dağıtımı) sunucuda ve web'de uçtan uca çalışıyor.
- Android'de lot bazlı satış ve satışların sunucuya gönderimi çalışıyor; çevrimdışı da satış yapılabiliyor.
- Hammadde alışı, stok, lotlar, lot hareket geçmişi ve transfer ekranları hazır.

**Testler:** 134 sunucu, 16 web, 17 Android testi geçiyor; çalışan sistemde bütünlük denetimi 8/8 tutarlı.

**Kalan büyük bloklar:** Görev 3 (izleme ve geri çağırma), iki yapay zekâ modeli, raporlar, derinlikli (3D) arayüz tasarımı, teslim paketi.

## 2. Gereksinim kapsamı

> **Güncelleme (27 Ekim akşam):** Aşağıda "Eksik" ya da "Kısmen" yazan yazılım ve belge maddelerinin hepsi bitti ve sınandı.
>
> - Görev 3, iade, fire, ters kayıt, yeniden işleme.
> - Demo profili, raporlar, iki yapay zekâ modeli ve raporu, 3D web ve Android.
> - Senkronizasyon açıklaması, CR-012 belgesi.
> - Kabul testleri: 23/23 (`reports/kabul_testleri.md`).
>
> Tablolar planlamanın ilk hâli olarak bırakıldı. **Kalanlar:**
>
> - Kişi 2'nin kendi bilgisayarında temiz kurulum (T-26) ve Android'i elle deneme.
> - Video (T-27).
> - GitHub'a yükleme ve e-posta (T-28).
>
> Teslim yardımcıları depo dışında: `AVATAR_Paylasim/Teslim/` (video senaryosu, e-posta taslağı, GitHub adımları, APK).

Durum: **Bitti** · **Kısmen** (ne eksik yazılı) · **Eksik** · İsteğe bağlı işler kapsam dışında. "Sahip" sütunu kalan işin sorumlusudur.

### Görev 1 ve ana veriler

| Gereksinim | Durum | Kalan iş | Sahip |
|---|---|---|---|
| FR-101 ürün kartları, FR-103 birimler, FR-301 cariler | Bitti | — | — |
| FR-102 alış, FR-207 fatura farkı | Bitti | — | — |
| FR-104 stok kırılımı | Bitti | — | — |
| FR-105…FR-108, FR-110, FR-111 dış üretim, EKP, kâr/marj | Bitti | — | — |
| FR-109 miktar farkları | Kısmen | Farklar emirde görünüyor; **üretim raporunda** da görünmeli (FR-602) | Kişi 1 |
| FR-112 geçmişe dönük inceleme | Bitti | — | — |

### Görev 2

| Gereksinim | Durum | Kalan iş | Sahip |
|---|---|---|---|
| FR-201…FR-208 reçete, dağıtım anahtarı, tartım, denge, dağıtım, parça lotları | Bitti | — | — |
| CR-012 örnek görseldeki tutarsızlıklar | Kısmen | Analiz `project_analysis.md` §3.3'te; teslim belgesinde ayrı ve açık bir bölüm olmalı (görsel PDF'te yok: S-01) | Kişi 2 |

### Görev 3 (izlenebilirlik ve geri çağırma)

| Gereksinim | Durum | Kalan iş | Sahip |
|---|---|---|---|
| FR-302 miktarlı çoktan çoğa lot bağları | Bitti | — | — |
| FR-303 hareket türleri | Kısmen | Eksik: müşteri iadesi, fire/imha, ters kayıt ucu | Kişi 1 |
| FR-304 ileri izleme, FR-305 geri izleme | Eksik | Lot ağı servisi hazır (`lot_graph.py`); API ve ekran yok | Kişi 1 |
| FR-306 geri çağırma, FR-307 liste + dışa aktarma | Eksik | `recalls`, `recall_lots`, `alerts` tabloları hazır | Kişi 1 |
| FR-308 ikinci kademe dağıtım | Eksik | `onward_deliveries` tablosu hazır | Kişi 1 |
| FR-309 zorunlu senaryo örnek kayıtlarla hazır | Kısmen | **Demo profili:** kurulumdan sonra ET-2026-001 → URT-2026-045 → SUC-2026-045 → Market A 30 / B 25 / C 30 hazır gelmeli | Kişi 1 |
| FR-310 bloke lot hiçbir kanaldan satılamaz | Bitti (sunucu) | Android'de bloke lotun görünümü ve açıklaması | Kişi 2 |

### Android satış ve senkronizasyon

| Gereksinim | Durum | Kalan iş | Sahip |
|---|---|---|---|
| FR-401…FR-405, TR-001, TR-002 | Bitti | — | — |
| TR-007 SQLite ↔ MySQL tutarlılığının açıklaması | Kısmen | `architecture.md` §5'te teknik anlatım var; değerlendiricinin okuyacağı kısa, şemalı bölüm (`docs/senkronizasyon.md`) | Kişi 2 |
| NFR-005 Android kullanılabilirlik | Kısmen | Derinlikli (3D) tasarım, bloke lot rozeti, eşitleme durumu | Kişi 2 |

### Yapay zekâ

| Gereksinim | Durum | Kalan iş | Sahip |
|---|---|---|---|
| FR-505 örnek veri seti ve varsayımlar | Eksik | T-18 sentetik veri üreticisi | Kişi 1 |
| FR-501 Model A, FR-503 Model B | Eksik | T-19, T-20 | Kişi 1 |
| FR-506 referans yöntem ve hata ölçümü, FR-507 sınırlılıklar, CR-006 YZ raporu | Eksik | T-19, T-20 + `reports/ai_degerlendirme.md` | Kişi 1 |
| FR-502, FR-504 tahmin–gerçek–sapma ekranda, TR-006 API entegrasyonu | Eksik | T-21 | Kişi 1 |
| FR-551, FR-552 | İsteğe bağlı | Kapsam dışı | — |

### Raporlar

| Gereksinim | Durum | Kalan iş | Sahip |
|---|---|---|---|
| FR-601 alış, FR-603 parçalama, FR-604 lot hareketleri, FR-605 satış | Kısmen | Rapor uçları (`/reports/*`) ve ekranları (süzgeç + CSV) | Kişi 1 |
| FR-602 üretim raporu | Kısmen | Rapor + YZ tahmin/sapma sütunu | Kişi 1 |
| FR-606 geri çağırma raporu | Eksik | T-16'dan sonra | Kişi 1 |
| FR-607 bütünlük raporu | Kısmen | Denetim servisi var; uç ve ekran yok | Kişi 1 |

### Kalite gereksinimleri

| Gereksinim | Durum | Kalan iş | Sahip |
|---|---|---|---|
| NFR-001, NFR-003, NFR-004 | Bitti | — | — |
| NFR-002 değişmez defter | Kısmen | Ters kayıt ucu ve düğmesi | Kişi 1 |
| NFR-005 kullanılabilirlik (web) | Kısmen | Derinlikli (3D) tasarım, Türkçe yardım metinleri | Kişi 1 |
| NFR-006 kurulabilirlik | Kısmen | Demo profili (Kişi 1); **temiz bilgisayarda** kurulum testi AT-14 (Kişi 2) | İkisi |
| NFR-007, NFR-008, NFR-010 | Bitti | — | — |
| NFR-009 performans (izleme < 2 sn) | Ölçülmedi | T-23'te ölçülür | Kişi 2 |

### Teslim

| Gereksinim | Durum | Kalan iş | Sahip |
|---|---|---|---|
| CR-007 veri modeli, CR-008 API açıklaması | Bitti | Son güncelleme | Kişi 1 |
| CR-009 örnek kayıtlar | Kısmen | Demo profili | Kişi 1 |
| CR-010 otomatik testler | Bitti | Kabul testleri T-23 | Kişi 2 |
| CR-011 üç görev ve iki YZ entegre | Kısmen | Görev 3 + YZ | Kişi 1 |
| CR-001 herkese açık GitHub, CR-005 son commit | Bekliyor | Depo `synera-avatar`; gönderim ön izleme ve onayla | Kişi 2 |
| CR-002 video ≤ 15 dk, CR-003 etkilenen marketlerin gösterimi | Bekliyor | T-27 | İkisi |
| CR-004 e-posta | Bekliyor | Kimin göndereceği açık (S-05) | Ekip kararı |

## 3. Kim neyin sahibi (dosya sahipliği)

| Kişi 1 — Caner: sunucu, web, yapay zekâ | Kişi 2 — arkadaş: Android, eşitleme, teslim |
|---|---|
| `backend/` (bütünü: servisler, uçlar, göçler, örnek kayıtlar, testler) | `android/` (bütünü), APK |
| `web/` (bütünü) | `tests/` (kök: uçtan uca kabul testleri) |
| `ml/`, `data/synthetic/`, `data/seed/` | `docs/senkronizasyon.md`, `docs/submission_checklist.md` |
| `docs/api.md`, `docs/data_model.md`, `docs/architecture.md` | `README.md` (teslim öncesi son hâli), `reports/kabul_testleri.md` |
| `reports/ai_degerlendirme.md` | `reports/gorev2_tutarsizliklar.md` (CR-012), video senaryosu |

**Ortak ve dikkat isteyen dosyalar** (çakışırsa iki tarafın satırları da tutulur):
- `CHANGELOG.md`, `reports/test_results.md`, `docs/development_plan.md` durum günlüğü: herkes kendi bölümünü sona ekler.
- Üretilen dosyalar (`docs/openapi.json`, `web/src/api/schema.d.ts`) elle birleştirilmez; birleştirmeden sonra API çalışırken yeniden üretilir (§5).

## 4. İşler

Süreler kaba tahmindir (kişi-saat). "Bitti" ölçütü sağlanmadan iş bitmiş sayılmaz (§7).

### Kişi 1 — Caner (sunucu, web, yapay zekâ)

| Sıra | İş | Gereksinim | Bitti ölçütü | Süre |
|---|---|---|---|---|
| 1 | **T-16a** İleri/geri izleme API: `GET /trace/forward/{lot}`, `/trace/backward/{lot}` (`api.md` §4.3) | FR-304, FR-305 | ET-2026-001 ileri izlemesi SUC-2026-045 ve Market A 30 / B 25 / C 30'u verir; SUC-2026-045 geri izlemesi üç hammadde lotunu, tedarikçileri, URT-2026-045'i verir | 3 |
| 2 | **T-16b** Geri çağırma: başlat (kaynak + bütün türevler bloke), liste, CSV, kapatma; uyarılar | FR-306, FR-307, FR-310 | Liste A/B/C'yi miktar + iletişimle verir, CSV iner; bloke sonrası satış reddedilir | 3 |
| 3 | **T-16c** İkinci kademe dağıtım; "kesin" ve "bilinen son alıcı, sonrası bilinmiyor" ayrımı | FR-308 | Kayıtlı ve kayıtsız iki örnek doğru ayrılır | 1,5 |
| 4 | **Eksik hareketler:** müşteri iadesi, fire/imha, ters kayıt | FR-303, NFR-002 | Her biri defter testleriyle; bütünlük 8/8 | 3 |
| 5 | **Demo profili** (`SEED_PROFILE=demo`, varsayılan): zorunlu senaryo + örnek parçalama + geçmiş kayıtlar; aynı servislerle | FR-309, CR-009 | Sıfırdan kurulumda senaryo hazır; bütünlük 8/8 | 2 |
| 6 | **T-17** Web: izleme, geri çağırma, uyarı, iade/fire ekranları | FR-304…FR-308 | ET-2026-001 senaryosu arayüzden yürür | 4 |
| 7 | **T-22** Raporlar: `/reports/*` + web rapor ekranları (süzgeç, CSV), bütünlük ekranı | FR-601…FR-607 | Her rapor demo verisiyle dolu | 4 |
| 8 | **Web derinlikli (3D) tasarım:** katmanlı kartlar, derinlikli menü, 3D lot akış şeması | NFR-005 | Masaüstü ve telefon genişliğinde okunaklı; testler yeşil | 3 |
| 9 | **T-18** Sentetik veri üreticisi (sabit tohum, varsayımlar belgede) | FR-505 | Aynı tohumla aynı veri | 2 |
| 10 | **T-19, T-20** Model A ve B + referans yöntem + hata ölçümü | FR-501, FR-503, FR-506 | Ayrılmış test verisinde hata tablosu | 5 |
| 11 | **T-21** YZ entegrasyonu: emir ve parçalamada tahmin kaydı, `/ai/*` uçları, ekranda tahmin–gerçek–sapma | FR-502, FR-504, TR-006 | Yeni emirde tahmin görünür; kabulden sonra sapma görünür; model yoksa iş akışı durmaz | 4 |
| 12 | **YZ raporu** `reports/ai_degerlendirme.md` | CR-006, FR-507 | Yöntem, veri, örnek tahminler, karşılaştırma, sınırlılıklar tek belgede | 2 |
| 13 | `api.md`, `data_model.md`, `architecture.md` son hâli | CR-007, CR-008 | Belgeler kodla tutarlı | 2 |
| | **Toplam** | | | ≈ 38 |

### Kişi 2 — ekip arkadaşı (Android, eşitleme, teslim)

| Sıra | İş | Gereksinim | Bitti ölçütü | Süre |
|---|---|---|---|---|
| 0 | **Kurulum:** paketten depoyu aç, `docker compose up --build`, testleri çalıştır; Android Studio ile uygulamayı emülatörde aç (`BASLA_BURADAN.md`) | — | Sunucu ve web testleri yeşil; emülatörde giriş + eşitleme | 2 |
| 1 | **Android derinlikli (3D) tasarım:** katmanlı kartlar, derinlik gölgeleri, dokunuşta hafif eğilme; ana ekran, stok, satış | NFR-005 | Emülatörde okunaklı; birim testleri yeşil | 3 |
| 2 | **Android geri çağırma görünümü:** bloke lot kırmızı rozetle görünür, satışta neden seçilemediği yazar; son eşitleme zamanı ve bekleyen satış sayısı | FR-403, FR-310 | Geri çağırmadan sonra eşitleme → lot bloke görünür, satılamaz | 2 |
| 3 | **Eşitleme açıklaması** `docs/senkronizasyon.md`: SQLite ↔ MySQL nasıl tutarlı kalır (çekme, gönderme, tekrar güvenliği, çevrimdışı ihlal) | TR-007 | Değerlendirici tek sayfada anlar; şemalı | 2 |
| 4 | **APK** üretimi ve kurulum notu | CR-001 | APK emülatöre/telefona kurulup giriş yapılır | 0,5 |
| 5 | **T-23** Kabul testleri: AT-01…AT-12, AT-15 çalışan sisteme karşı otomatik (`tests/`); izleme süresini ölç | CR-010, NFR-009 | `reports/kabul_testleri.md`'de hepsi yeşil; izleme < 2 sn | 6 |
| 6 | **CR-012** Görev 2 görselindeki tutarsızlıklar: `reports/gorev2_tutarsizliklar.md` (287,50 ≠ 351,00; parçalar 22 kg) | CR-012 | Hesaplar ve bizim çözümümüz açık | 1 |
| 7 | **T-26** Temiz kurulum testi kendi bilgisayarında: yalnız README adımlarıyla | NFR-006, AT-14 | Sorunsuz kuruluyor ya da sorunlar bildirildi | 2 |
| 8 | **GitHub:** `synera-avatar` deposu (gizli), Kişi 1 ortak çalışan; README son hâli, `submission_checklist.md` | CR-001, CR-005 | Gönderim ön izleme ve onayla; teslimde herkese açık | 1 |
| 9 | **T-27 (payı)** Video senaryosu, süre provası (≤ 15 dk), yükleme (YouTube liste dışı ya da Drive) | CR-002, CR-003 | Bağlantı oturum kapalı tarayıcıda açılıyor | 3 |
| | **Toplam** | | | ≈ 22,5 |

### Birlikte

| İş | Ne zaman |
|---|---|
| Günlük birleştirme (§5) ve kısa kontrol: testler + bütünlük + ana senaryo | Her akşam |
| T-27 video çekimi (emülatör ve web hazır) | 31 Ekim |
| T-28 teslim: `submission_checklist.md`; depo herkese açık; e-posta (ext.s.a.bakir@delta-ac.de, konu "Synera", adres elle yazılır) | 1 Kasım |
| T-02 açık sorular: S-01 (Görev 2 görseli), S-05 (e-postayı kim gönderir), kişi adları | Bugün |

## 5. Birlikte çalışma

**Ortak depo:** GitHub'a kod, ekip kararıyla son gün ve ön izlemeyle yüklenir. O zamana kadar kod **git paketi** (`.bundle` dosyası) ile taşınır (WhatsApp, Drive ya da USB). Kişi 1 birleştirmeden sorumludur; `main` dalı onda tutulur.

Kişi 2 başlangıçta (bir kez):

```bash
git clone AVATAR_Synera.bundle AVATAR_Yarisma
```

```bash
cd AVATAR_Yarisma && git switch -c kisi2
```

Kişi 2 günün işini gönderir (`main`'den sonra yaptığı commit'ler):

```bash
git bundle create kisi2_28ekim.bundle main..kisi2
```

Kişi 1 alır ve birleştirir (`main` dalındayken):

```bash
git fetch ../kisi2_28ekim.bundle kisi2:kisi2 && git merge kisi2
```

Kişi 1 birleşmiş `main`'i geri gönderir:

```bash
git bundle create main_28ekim.bundle main
```

Kişi 2 alır ve kendi dalına katar:

```bash
git switch main && git pull ../main_28ekim.bundle main && git switch kisi2 && git merge main
```

**Kurallar:**
- Commit'ler küçük ve anlamlı, mesajlar Türkçe. Her commit'ten önce o kısmın testleri geçmeli.
- Birleştirmeden sonra, API çalışırken üretilen dosyalar tek komutla yenilenir: `sh scripts/api_tipleri_yenile.sh`.
- `.env`, parola, `_kaynak/` ve yarışma belgeleri depoya girmez (CON-006).
- Port çakışması varsa `.env` ile değiştirilir: `API_PORT=18000`, `WEB_PORT=18080`.
- Model eğitimi ve sunucu testleri Docker içinde (Linux) çalıştırılır.

## 6. İki kulvar arasındaki sözleşme (eşitleme API'si)

Android kulvarı sunucuya yalnız iki uçla bağlanır; bu uçların biçimi değişmeden önce iki kişi anlaşır.

- **`GET /sync/pull?since=N`** (`api.md` §4.4): N'den sonra değişen ürünler, müşteriler, araç deposundaki lotlar (durumları dahil: `AKTIF` / `BLOKE`) ve araç stoku. `dataset_id` değişmişse ya da `next_since < since` ise cihaz yerel kopyayı silip baştan çeker.
- **`POST /sync/push`**: bekleyen satışlar; her satış cihazda üretilen `client_uuid` ile gelir. Yanıt satış başına `ACCEPTED`, `ACCEPTED_WITH_WARNING` (çevrimdışıyken bloke lot satıldı), `DUPLICATE` ya da `REJECTED`.
- **Geri çağırma:** Sunucu bir lotu bloke edince lotun değişiklik numarası artar; bir sonraki çekmede cihaz lotu `BLOKE` görür ve satışa kapatır.
- **Para ve miktar** metin ondalık olarak taşınır (ADR-006); Android'de kuruş ve gram olarak tam sayıyla tutulur.

## 7. "Bitti" tanımı

Bir iş ancak şunların hepsi olunca biter:

1. Kod ve testler yazıldı; o kısmın bütün testleri geçiyor (sunucu: `pytest`, `ruff`; web: `tsc`, `oxlint`, `vitest`; Android: `gradlew testDebugUnitTest`).
2. Çalışan sistemde elle denendi; bütünlük denetimi 8/8.
3. `reports/test_results.md`'ye sonuç, `CHANGELOG.md`'ye kısa kayıt, `development_plan.md`'de durum satırı yazıldı.
4. Gerekiyorsa `api.md` / `data_model.md` güncellendi.
5. Yerel commit atıldı (GitHub'a değil).

## 8. Takvim

| Gün | Kişi 1 — Caner | Kişi 2 — arkadaş | Akşam kontrolü |
|---|---|---|---|
| 27 Ekim Sal | T-16 izleme + geri çağırma API, demo profili | Kurulum, Android Studio, GitHub deposu (gizli) | Arkadaşta testler yeşil |
| 28 Ekim Çar | Eksik hareketler, T-17 web ekranları | Android derinlikli tasarım, bloke lot görünümü | **Birleştirme 1** |
| 29 Ekim Per (tatil) | T-18…T-21 yapay zekâ, YZ raporu | Eşitleme açıklaması, CR-012, APK | **Birleştirme 2** — M3: üç görev + YZ çalışıyor |
| 30 Ekim Cum | T-22 raporlar, web derinlikli tasarım | T-23 kabul testleri | **Birleştirme 3** — M4: kabul testleri yeşil |
| 31 Ekim Cmt | Belgeler, hata düzeltme | T-26 temiz kurulum, video senaryosu | **Kod dondurma 20:00**, video çekimi — M5 |
| 1 Kasım Paz | GitHub'a gönderim (ön izleme + onay) | Depo herkese açık, video bağlantısı denemesi | Kontrol listesi tam; **e-posta öğleden sonra** — M6 |

**Geride kalınırsa önce bunlar bırakılır** (`development_plan.md` §5): yeniden işleme hareketi, rapor süzgeçleri, görsel cila. ★K gereksinimlerden (Görev 3, iki YZ modeli, demo senaryosu, video) hiçbiri kısılmaz.
