# Geliştirme Planı

| | |
|---|---|
| Sürüm | v0.1 (öneri — ekip bilgisi (S-02) ve teknoloji kararlarından sonra kesinleşir) |
| Tarih | 24 Ekim 2026 |
| Son teslim | **1 Kasım 2026 23:59** (Türkiye saati esas — AS-010) |
| Hedef teslim | 1 Kasım öğleden sonra; **kod dondurma 31 Ekim akşamı** |

## 1. Yaklaşım

1. **Önce çalışan en küçük sürüm.** Değerlendirme odağındaki beş madde (★K gereksinimler) bitmeden hiçbir bonus işe başlanmaz.
2. **Ortak çekirdek önce.** Hareket defteri, lot ağı ve maliyet motoru üç görevin temelidir; bunlar testleriyle birlikte erken biter.
3. **Dikey dilimler.** Her görev, veritabanından ekrana kadar uçtan uca çalışır hâle getirilip sonra diğerine geçilir. Böylece hangi gün dursak elimizde gösterilebilir bir sistem olur.
4. **Paralel kulvarlar.** Backend, Web, Android ve YZ dört kulvarda paralel ilerler; aradaki sözleşme API tanımıdır (T-04). Her akşam kulvarlar birleştirilip kabul testleri çalıştırılır.
5. **Her iş adımı:** hedef → gereksinim → tasarım → uygulama → kontrol → test → değerlendirme → belge → durum güncellemesi.

## 2. Takvim ve kilometre taşları

| Gün | Tarih | Odak | Kilometre taşı (akşam kontrolü) |
|---|---|---|---|
| 1 | 24 Ekim Cmt | Analiz ✓, sorular, teknik araştırma | — |
| 2 | 25 Ekim Paz | Teknoloji kararları, mimari, veri modeli, API sözleşmesi, ortam kurulumu | **M1:** mimari + API sözleşmesi onaylı; her bileşende "merhaba dünya" çalışıyor |
| 3 | 26 Ekim Pzt | Çekirdek (şema, defter, lot ağı, maliyet motoru); Android iskeleti; sentetik veri | — |
| 4 | 27 Ekim Sal | Görev 1 uçtan uca; Android satış ekranı; Model A | **M2:** Görev 1 API+web çalışıyor, maliyet testleri yeşil; Android sunucudan veri çekiyor |
| 5 | 28 Ekim Çar | Görev 2; Android senkronizasyon; Model B | — |
| 6 | 29 Ekim Per (tatil) | Görev 3 (izleme, geri çağırma); Android bloke; YZ servisi entegrasyonu | **M3:** üç görev + Android satış/senkron + iki model çalışıyor |
| 7 | 30 Ekim Cum | Raporlar, uçtan uca testler, hata düzeltme; bonus kararı | **M4:** bütün kabul testleri yeşil |
| 8 | 31 Ekim Cmt | Belgeler, temiz kurulum testi, APK, demo provası, video | **M5:** kod dondurma, video çekildi |
| 9 | 1 Kasım Paz | Son kontrol, depo herkese açık, e-posta | **M6:** teslim (öğleden sonra) |

29 Ekim resmî tatil; ekip çalışmayacaksa M3 30 Ekim'e kayar ve bonus iş tamamen çıkar.

## 3. İş listesi

Kulvarlar: **B** Backend · **W** Web · **A** Android · **Y** Yapay zekâ · **E** Entegrasyon/teslim.
Öncelik: ★K kritik · Z zorunlu · İ isteğe bağlı. Süreler kaba tahmindir (kişi-saat).

### P0 — Hazırlık

| Kimlik | İş | Kulvar | Önc. | Bağımlılık | Çıktı ve tamamlanma ölçütü | Test / doğrulama | Süre | Risk | Durum |
|---|---|---|---|---|---|---|---|---|---|
| T-01 | Proje analizi, gereksinim taslağı, klasör yapısı | E | ★K | — | `project_analysis.md`, `requirements.md` v0.1, klasör iskeleti | Ekip incelemesi | 4 | — | **Tamamlandı (ekip incelemesi bekliyor)** |
| T-02 | Soruların cevaplanması; gereksinimler v1.0 | E | ★K | T-01 | S-01…S-15 cevaplı; varsayımlar güncel | Ekip onayı | 2 | Gecikme tüm planı kaydırır | **Sürüyor** — S-02, S-03, S-11, S-14…S-17 cevaplandı; S-01 (Görev 2 görseli) ve S-05 (GitHub hesabı, e-postayı kim gönderir) kısmen; diğerlerinde önerilen varsayımla ilerleniyor; kişi adları bekleniyor |
| T-03 | Teknik araştırma ve teknoloji kararları | E | ★K | T-02 (S-02, S-03) | `technical_research.md`, `docs/decisions/ADR-001…007` | Ekip onayı | 4 | Yanlış seçim → öğrenme maliyeti | **Tamamlandı** — ADR-001…007 kabul edildi (24 Ekim) |
| T-04 | Mimari, veri modeli (ER), API sözleşmesi, senkronizasyon tasarımı | B | ★K | T-03 | `architecture.md`, `data_model.md`, `api.md`, ADR-008 | AT senaryolarının sade model üzerinde çalıştırılması (`reports/design_validation/`) | 5 | R-04, R-05 | **Tamamlandı (ekip incelemesi bekliyor)** — tasarım doğrulaması 20/20 |
| T-05 | Ortam kurulumu: Docker Desktop'ı açma, MySQL 8.4 konteyneri, Python/FastAPI iskeleti, React iskeleti, **Android Studio + SDK kurulumu** (S-14), depo | E | ★K | T-03 | Her bileşende "merhaba dünya"; depo (GitHub'a gönderim öncesi onay) | Elle kontrol | 4 | R-06, R-08 | **Tamamlandı** — sunucu, web, MySQL; Android Studio 2026.2.1, SDK 37, emülatör (Android 17 imajı, WHPX hızlandırma) çalışıyor (`reports/test_results.md`). Yerel git henüz yok (GitHub proje sonunda) |

### P1 — Çekirdek

| Kimlik | İş | Kulvar | Önc. | Bağımlılık | Çıktı ve tamamlanma ölçütü | Test / doğrulama | Süre | Risk | Durum |
|---|---|---|---|---|---|---|---|---|---|
| T-06 | Veritabanı şeması, şema göçleri, örnek kayıt yükleyici | B | ★K | T-04, T-05 | Şema tek komutla kurulur; senaryo kayıtları yüklenir | Entegrasyon testi | 4 | — | **Tamamlandı** — 31 tablo, defter tetikleyicileri, `base` örnek kayıtları; 23/23 test. Hammadde alışlarının örnek kaydı T-07'ye kaldı (defter üzerinden yazılmalı) |
| T-07 | Hareket defteri + lot ağı servisleri (tek ortak "hareket yaz / lot bağla" yolu) | B | ★K | T-06 | Lotsuz hareket imkânsız; stok = Σ hareket | AT-10 | 5 | R-03, R-04 | **Tamamlandı** — `services/ledger.py`, `lot_graph.py`, `integrity.py`; ek olarak alış servisi, belge numaralandırma, senkron değişiklik numarası, API hata biçimi |
| T-08 | Maliyet motoru: ondalık aritmetik, EKP, dağıtım, kuruş kuralı | B | ★K | T-04 | Şartname rakamları birebir | AT-01, AT-02, AT-03 | 4 | R-02 | **Tamamlandı** — `domain/` (money, costing, allocation, balance, graph); 78/78 test |

### P2 — Görev 1

| Kimlik | İş | Kulvar | Önc. | Bağımlılık | Çıktı ve tamamlanma ölçütü | Test / doğrulama | Süre | Risk | Durum |
|---|---|---|---|---|---|---|---|---|---|
| T-09 | Görev 1 API: kartlar, alış, dış üretim emri, sevk, hizmet, kabul, farklar, EKP/VKP | B | ★K | T-07, T-08 | URT-2026-045 senaryosu API'den baştan sona yürür | AT-01, AT-02, AT-15 | 5 | — | **Tamamlandı** — `services/production.py` + ana veri, alış, lot, transfer, üretim emri uçları; 111/111 test; canlı senaryo sunucuda ve telefonda geçti. Model A tahmini T-21'de |
| T-10 | Görev 1 web ekranları | W | ★K | T-09 | Senaryo arayüzden yürür; EKP dökümü görünür | Elle senaryo + bileşen testi | 5 | — | **Tamamlandı** — 13 ekran; tarayıcıda alış → emir → sevk → kabul → araca yükleme senaryosu geçti; saf fonksiyonlar için 16 Vitest testi (bileşen testi yazılmadı; arayüz akışları T-23'te otomatikleşecek) |

### P3 — Görev 2

| Kimlik | İş | Kulvar | Önc. | Bağımlılık | Çıktı ve tamamlanma ölçütü | Test / doğrulama | Süre | Risk | Durum |
|---|---|---|---|---|---|---|---|---|---|
| T-11 | Parçalama API: reçete, dağıtım anahtarı, giriş, ağırlık dengesi, dağıtım, tutarlılık uyarısı, parça lotları | B | ★K | T-07, T-08 | Örnek parçalama kaydedilir; Σ dağıtım = toplam | AT-03, AT-04, AT-05 | 5 | R-02 | **Tamamlandı** — `services/cutting.py` + reçete ve parçalama uçları; AT-03 iki yöntemde birebir, AT-04 reddi; 126/126 test; canlı senaryo geçti. Model B tahmini T-21'de |
| T-12 | Parçalama web ekranları | W | ★K | T-11 | Tartım girişi, denge göstergesi, dağıtım dökümü | Elle senaryo | 4 | — | **Tamamlandı** — parçalama listesi, yeni parçalama, tartım (canlı denge ve dağıtım ön izlemesi), onay sonucu, reçeteler; tarayıcıda baştan sona denendi |

### P4 — Android

| Kimlik | İş | Kulvar | Önc. | Bağımlılık | Çıktı ve tamamlanma ölçütü | Test / doğrulama | Süre | Risk | Durum |
|---|---|---|---|---|---|---|---|---|---|
| T-13 | Android iskeleti: proje, SQLite şeması, API istemcisi, giriş ekranı | A | ★K | T-04, T-05 | Emülatörde açılır, sunucudan ana veri çeker | Elle + birim testi | 4 | R-06 | **Tamamlandı** — emülatörde giriş → çekme → araç stoku → bloke işareti denendi; sunucuya `/auth/login`, `/auth/me`, `/sync/pull` eklendi; Android 17 yerel ağ izni çözüldü |
| T-14 | Satış akışı: müşteri, lot seçimi, satır = lot = hareket; bloke lot engeli | A | ★K | T-13, T-09 | Market A/B/C satışları cihazdan yapılır | AT-08 (cihaz) | 6 | — | **Tamamlandı** — satış ekranı (müşteri, ilk biten önerili lot listesi, miktar/fiyat, bloke lot engeli), cihazda tek işlemde kayıt, kullanılabilir miktar = sunucu − bekleyen; emülatörde denendi |
| T-15 | Senkronizasyon (aşağı: ana veri, lot durumu, stok; yukarı: satış, tekrar güvenli) + çevrimdışı çalışma | A+B | ★K | T-14 | Çevrimdışı satış bağlantı gelince bir kez işlenir | AT-11, AT-12 | 6 | R-05 | **Tamamlandı** — sunucuda `POST /sync/push` (UUID ile tekrar güvenli, satış başına alt işlem, ihlal uyarısı), cihazda önce gönder sonra çek + WorkManager; uçak modunda satış → bağlantı gelince gönderim denendi |

### P5 — Görev 3

| Kimlik | İş | Kulvar | Önc. | Bağımlılık | Çıktı ve tamamlanma ölçütü | Test / doğrulama | Süre | Risk | Durum |
|---|---|---|---|---|---|---|---|---|---|
| T-16 | İleri/geri izleme API; geri çağırma (bloke, liste, dışa aktarma, ikinci kademe) | B | ★K | T-07 | ET-2026-001 → A 30 / B 25 / C 30 | AT-06…AT-09 | 6 | R-04 | Bekliyor |
| T-17 | İzleme ve geri çağırma web ekranları | W | ★K | T-16 | Tek ekranda zincir + alıcı listesi + bloke düğmesi | Elle senaryo | 4 | — | Bekliyor |

### P6 — Yapay zekâ

| Kimlik | İş | Kulvar | Önc. | Bağımlılık | Çıktı ve tamamlanma ölçütü | Test / doğrulama | Süre | Risk | Durum |
|---|---|---|---|---|---|---|---|---|---|
| T-18 | Sentetik veri üreticisi + varsayım belgesi | Y | ★K | T-04 | `data/synthetic/` + açıklama; tohum sabit, yeniden üretilebilir | Veri dağılım kontrolü | 3 | R-07 | Bekliyor |
| T-19 | Model A + referans yöntem + değerlendirme | Y | ★K | T-18 | Test verisinde hata tablosu | AT-13 | 4 | R-07 | Bekliyor |
| T-20 | Model B + referans yöntem + değerlendirme | Y | ★K | T-18 | Test verisinde parça bazlı hata tablosu | AT-13 | 4 | R-07 | Bekliyor |
| T-21 | YZ servisi (API) + backend bağlantısı + ekranlarda tahmin/gerçek/sapma | Y+B+W | ★K | T-19, T-20, T-09, T-11 | Üretim ve parçalama ekranlarında tahmin görünür | Entegrasyon testi | 5 | R-08 | Bekliyor |

### P7 — Raporlar ve bütünleştirme

| Kimlik | İş | Kulvar | Önc. | Bağımlılık | Çıktı ve tamamlanma ölçütü | Test / doğrulama | Süre | Risk | Durum |
|---|---|---|---|---|---|---|---|---|---|
| T-22 | Altı rapor (FR-601…606) | W+B | Z | T-09, T-11, T-15, T-16 | Raporlar örnek kayıtlarla dolu | Elle + API testi | 5 | — | Bekliyor |
| T-23 | Uçtan uca kabul testleri (AT-01…AT-12, AT-15) otomatik; hata düzeltme | E | ★K | P1–P5 | Bütün kabul testleri yeşil | Test raporu | 6 | R-01 | Bekliyor |
| T-24 | Bonus: anomali uyarıları (FR-552) | Y+B | İ | T-21, **T-23 yeşil** | Fire/verim/maliyet anomalileri işaretlenir | Örnek anomali testi | 4 | Kapsam kayması | **Plandan çıkarıldı** (2 kişilik ekip); M4'te zaman kalırsa geri alınır |

### P8 — Teslim

| Kimlik | İş | Kulvar | Önc. | Bağımlılık | Çıktı ve tamamlanma ölçütü | Test / doğrulama | Süre | Risk | Durum |
|---|---|---|---|---|---|---|---|---|---|
| T-25 | Belgeler: README kurulum, veri modeli, API, senkronizasyon, YZ raporu, tutarsızlık açıklaması | E | ★K | Tümü | Belgeler kodla tutarlı | Çapraz okuma | 5 | — | Bekliyor |
| T-26 | Temiz klonda kurulum testi + APK üretimi | E | ★K | T-25 | README adımlarıyla sıfırdan çalışır | AT-14 | 2 | R-09 | Bekliyor |
| T-27 | Demo senaryosu, prova, video çekimi ve yükleme | E | ★K | T-23 | ≤ 15 dk video, bağlantı herkese açık | Süre ölçümü, izleme testi | 4 | R-11 | Bekliyor |
| T-28 | Teslim kontrol listesi, depoyu herkese açma, e-posta (ekip gönderir) | E | ★K | T-26, T-27 | `submission_checklist.md` tamamen işaretli | Kontrol listesi | 1 | R-12 | Bekliyor |

## 4. İş yükü ve kritik yol

- **Toplam kaba tahmin:** bonus hariç ≈ **116 kişi-saat** (tablodaki sürelerin toplamı, T-01 dahil). 24 Ekim sonunda ≈ 39 saati tamamlandı (T-01, T-03…T-09, T-13); kalan ≈ **77 kişi-saat** (T-02'nin 2 saati dahil).
- **Ekip 2 kişi (24 Ekim).** 8 günde (25 Ekim – 1 Kasım) kişi başı ≈ 39 saat, yani günde ≈ 5 saat demek; pay az. Ekibin zamanı inceleme, deneme, Android Studio'daki işler, karar ve video çekimine gider. Yine de pay az olduğu için §5'teki kısma sırası **baştan uygulanır**: T-24 (bonus) ve FR-406 plandan çıkarıldı. Yeniden zaman kalırsa geri alınır.
- **Kritik yol:** T-02 → T-03 → T-04 → T-06 → T-07 → T-09 → T-14 → T-15 → T-23 → T-27 → T-28. Bu zincirdeki her gecikme teslimi doğrudan kaydırır.

### Rol dağılımı (27 Ekim'den itibaren — ayrıntı: [is_bolumu.md](is_bolumu.md))

T-13…T-15 (Android) ve T-06…T-12 bitti; kalan işler birbirinin dosyalarına en az dokunacak biçimde bölündü.

| Kişi | Kulvarlar | Kalan işler | Ek sorumluluk |
|---|---|---|---|
| **Kişi 1 — Caner** | Sunucu (B), Web (W), Android bakım | T-16, T-17, demo profili (FR-309), eksik hareketler (iade, fire, ters kayıt), T-22, T-25 (belgeler), APK | **Entegrasyon sorumlusu:** `main` dalı, her akşam birleştirme, API sözleşmesi |
| **Kişi 2 — ekip arkadaşı** | Yapay zekâ (Y), Entegrasyon/teslim (E) | T-18…T-21, YZ raporu, T-23, T-26 (kendi bilgisayarında temiz kurulum), video senaryosu | Kabul testleri, kurulum testi |
| İkisi birlikte | — | T-27 video, T-28 teslim, T-02 açık sorular | — |

Gerekçe: YZ (`ml/`) ve kabul testleri (`tests/`) kendi klasörlerinde, sunucuya tek bir sözleşmeyle (`is_bolumu.md` §6) bağlanıyor. Projeye sonradan katılan kişi, var olan defter ve lot ağı koduna dokunmadan çalışabiliyor. Görev 3 ise defter ve lot ağıyla iç içe; onu bu kodu yazan kulvar alıyor.

## 5. Geride kalırsak kapsam kısma sırası

Önce en alttakiler bırakılır; ★K gereksinimlerden hiçbiri kısılmaz.

1. T-24 anomali uyarıları (bonus)
2. FR-406 Android operasyon ekranları
3. FR-402 SKT'ye göre lot önerisi
4. Web ekranlarında görsel cila (işlev kalır)
5. FR-601/603/605 raporlarında süzgeç seçenekleri (rapor kalır)

## 6. Durum günlüğü

| Tarih | Ne yapıldı | Sıradaki |
|---|---|---|
| 24 Ekim 2026 | Şartname ve e-posta incelendi; PDF'te Görev 2 görselinin olmadığı tespit edildi; analiz, gereksinim taslağı, test stratejisi, plan ve klasör iskeleti oluşturuldu (T-01). Kod yazılmadı, hiçbir test çalıştırılmadı. | T-02: soruların cevaplanması |
| 24 Ekim 2026 (2) | Ekip cevapları işlendi: takım adı Synera, teslim adresi ext.s.a.bakir@delta-ac.de, Go yok (Kotlin/Python), gerçek veri yok. Diğer iki PDF'in ilkiyle birebir aynı olduğu, hiçbirinde görsel olmadığı doğrulandı. Ortam yoklandı: Android Studio/SDK yok, Docker Desktop kapalı. Teknik araştırma yazıldı; ADR-001…007 önerildi (T-03). | Kararların onayı; S-02, S-14, S-15; sonra T-04 mimari |
| 24 Ekim 2026 (3) | ADR-001…007 ekipçe kabul edildi. Mimari (`architecture.md`), veri modeli (`data_model.md`), API sözleşmesi (`api.md`) ve ADR-008 (stok defteri) yazıldı. Tasarımın sade bir kopyası şartname senaryolarıyla çalıştırıldı: 20/20 kontrol geçti (ürün testi değil). Kod yazılmadı. | T-05 ortam kurulumu; S-02, S-14, S-15 |
| 24 Ekim 2026 (4) | ADR-008 ve mimari onaylandı. T-05: Docker Desktop'ın açılmasını engelleyen eski soket dosyası sorunu giderildi; FastAPI + Alembic iskeleti, React + Vite + TypeScript + antd iskeleti ve Docker Compose (MySQL 8.4.13) kuruldu. Sağlık kontrolü uçtan uca çalışıyor; pytest 2/2, ruff ve oxlint temiz. Android Studio kurulumu winget ile başlatıldı, lisans onayı kullanıcıda. Karar: proje bitene kadar GitHub'a gönderim yok. | Android Studio kurulumu + Android iskeleti (T-13 başı); yerel git kararı; T-06 şema |
| 24 Ekim 2026 (5) | Ekip 2 kişi olarak teyit edildi; rol dağılımı önerildi; bonus (T-24) ve FR-406 baştan plandan çıkarıldı. PostgreSQL sorusu cevaplandı: şartnamede MySQL zorunlu (S-17); MySQL ile devam önerildi. | T-06 şema (Kişi 1), Android iskeleti (Kişi 2) |
| 24 Ekim 2026 (6) | T-06 tamamlandı: 31 tablonun modelleri, ilk Alembic göçü (+ UPDATE/DELETE engelleyen iki tetikleyici, senkron sayacı), ayrı test veritabanı (`avatar_test`), `base` örnek kayıtları (10 ürün, 10 cari, 3 depo, 2 demo kullanıcı, kuzu reçetesi, URT-2026-045'i üretecek sayaç). 23/23 test, ruff temiz. 4 sorun giderildi (`reports/test_results.md`). | T-07 defter + lot ağı, T-08 maliyet motoru |
| 24 Ekim 2026 (7) | T-07 ve T-08 tamamlandı: deftere tek yazma yolu (bloke, eksi stok, değerleme, ters kayıt), lot ağı ve izleme gezinmesi, maliyet/dağıtım/denge fonksiyonları, alış servisi, numaralandırma, bütünlük denetimi (I-1…I-8), senkron değişiklik numarası, API hata biçimi. Hammadde alışları örnek kayıtlara defter üzerinden eklendi (ET-2026-001 vb.). 78/78 test; çalışan sistemde 8/8 değişmez tutarlı. | T-09 Görev 1 API (dış üretim emri), T-11 parçalama API |
| 24 Ekim 2026 (8) | T-13 tamamlandı: Android projesi (Gradle 9.8.2, AGP 9.4.1, Kotlin 2.4.21, Compose, Room, Retrofit), giriş ve ana ekran, Room tabloları, çekme senkronu; sunucuda giriş/oturum/çekme uçları (89 test). Emülatörde uçtan uca denendi. Android 17'nin yerel ağ izni (`ACCESS_LOCAL_NETWORK`) bulundu ve çözüldü. T-05 de tamamlandı (Android ortamı). R-06 kapandı. | T-09 dış üretim emri (Kişi 1), T-14 Android satış ekranı (Kişi 2) |
| 24 Ekim 2026 (9) | T-09 tamamlandı: dış üretim emri (oluştur, sevk, kabul, iptal; hizmet faturası farkı açıklama ister; iade; miktar farkları; EKP/VKP/kâr/marj; verim), ana veri, alış, lot ayrıntısı/hareketleri ve transfer uçları; 111/111 test. Canlı senaryoda URT-2026-045 → SUC-2026-045 = 1.543,50 €, EKP 18,16 €, marj %27,07; araca yüklenen 85 paket telefonda göründü. İki hata bulunup düzeltildi: kayıt yanıttan sonra yapılıyordu; sunucu sıfırlanınca telefon eski kayıtları tutuyordu (`reports/test_results.md`). Yerel git kaydı başlatıldı; uzak depo yok, gönderim proje bitince. | T-10 Görev 1 web ekranları (Kişi 1), T-14 Android satış (Kişi 2) |
| 24 Ekim 2026 (10) | T-10 tamamlandı: Görev 1 web ekranları — giriş/çıkış, ürün ve cari kartları, hammadde alışı (fatura farkı açıklaması, ek maliyetler, ön izleme), stok durumu (lot/ürün/depo), lot listesi ve ayrıntısı (hareket geçmişi: belge no + kullanıcı, lot ağı, toplam = kalan denetimi), transfer (araca yükleme), dış üretim emri (oluştur, sevk, kabul, iptal, EKP dökümü, kâr/marj, verim). API tipleri OpenAPI'den üretiliyor. Sunucuya: `/stock`, `/auth/logout`, hareketlerde belge no ve kullanıcı, UTC zaman eki, dış üreticiye otomatik depo. 113 sunucu testi, 16 web birim testi; senaryo tarayıcıda baştan sona denendi, 3 hata bulunup düzeltildi. | T-11 parçalama API (Kişi 1), T-14 Android satış (Kişi 2) |
| 24 Ekim 2026 (11) | T-11 tamamlandı: parçalama — reçete (Σ oran = 1, fire ürünsüz ve maliyetsiz, değer yönteminde €/kg zorunlu), taslak → tartım → ön izleme (kaydetmeden) → onay; ağırlık dengesi toleranslı; dağıtım iki yöntemle (AT-03 birebir: 123,41/83,34/72,12/33,66/38,47 ve 111,68/63,82/79,77/47,87/47,86); fire girilmeden onay reddi (AT-04); parça lotları (`BUT-PRC-2026-012` …), lot bağları, SKT girdi lotunu geçmez; kısmi parçalamada orantılı maliyet. Sunucu mesajlarındaki sayılar Türkçe biçime çevrildi ("3.000 kg" yanlış okunuyordu). 126 test. | T-12 parçalama web ekranları (Kişi 1), T-14 Android satış (Kişi 2) |
| 24 Ekim 2026 (12) | T-12 tamamlandı: parçalama web ekranları — liste, yeni parçalama (reçete → ana depodaki giriş lotu → ağırlık), tartım ekranı (her girişte sunucudan kaydetmeden ön izleme: denge göstergesi, iki yöntemle pay ve €/kg), onay ve sonuç (dağıtım dökümü, parça lotları), reçete listesi ve yeni reçete (oranlar yüzde, toplam %100 denetimi). Görev 2 uçtan uca arayüzden yürüyor. | T-14 Android satış (Kişi 2), T-16 izleme ve geri çağırma API (Kişi 1) |
| 24 Ekim 2026 (13) | T-14 ve T-15 tamamlandı: Android satış (müşteri, lot seçimi FEFO, bloke lot engeli, cihazda tek işlemde kayıt; Room sürüm 3) ve gönderim (önce gönder sonra çek; WorkManager ağ gelince gönderir). Sunucuda `POST /sync/push` (AT-11: aynı satış iki kez → tek kayıt; yetersiz stokta yalnız o satış reddedilir; AT-12: çevrimdışı bloke lot satışı kaydedilir, ihlal işaretlenir, uyarı düşer) ve `GET /sales`. Emülatörde Market A 30 / B 25 adet satıldı (maliyetler 544,76 / 453,97 €), uçak modundaki iki satış bağlantı gelince gönderildi. 134 sunucu, 17 Android testi. | T-16 izleme ve geri çağırma API (Kişi 1), T-17 web ekranları |
| 27 Ekim 2026 (14) | İki kişilik iş bölümü yapıldı (`is_bolumu.md`): bütün gereksinimlerin kapsamı çıkarıldı (biten / kısmen / eksik ve sahibi), dosya sahipliği, iki kulvar arası YZ sözleşmesi, günlük birleştirme (git paketi), "bitti" tanımı ve 1 Kasım'a kadar takvim. Ekip arkadaşı için kurulum paketi hazırlandı. Testler yeniden çalıştırıldı: 134 sunucu, 16 web, 17 Android. Bulgu: 8000 portu bu bilgisayarda başka bir projede; `API_PORT`/`WEB_PORT` ile değiştirilebiliyor. | Kişi 1: T-16 + demo profili; Kişi 2: kurulum + T-18 |
| 27 Ekim 2026 (15) | İş bölümü kulvarlara göre yeniden yazıldı (Kişi 1: sunucu, web, YZ; Kişi 2: Android, eşitleme, teslim). T-16, T-17, eksik hareketler (iade, fire, ters kayıt), demo profili, T-18…T-22 tamamlandı; web ve Android'e derinlikli (3D) arayüz. Testler: 166 sunucu, 4 YZ, 16 web, 17 Android; demo profili temiz kopyada sıfırdan kuruldu, senaryo tarayıcıda denendi. | Kişi 2: kurulum, kabul testleri; birlikte: video |
| 27 Ekim 2026 (16) | Yeniden işleme hareketi eklendi (FR-303 tam). T-23 kabul testleri 23/23 (çalışan sisteme, ayrı kopyada sıfırdan kurulumla — AT-14). Paketten temiz kurulum provası: bütün testler geçti, APK üretildi. Teslim klasörü: video senaryosu, e-posta taslağı, GitHub yükleme adımları, APK. | Kalan: arkadaşın bilgisayarında T-26, video çekimi, GitHub'a yükleme (onayla), e-posta |
