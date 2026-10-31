# Değişiklik Geçmişi

Biçim: her kayıt tarih, ne değişti ve neden. Yalnızca gerçekten yapılmış işler yazılır.

## [Yayımlanmamış]

### 24 Ekim 2026
- Proje klasörü ve belge iskeleti oluşturuldu.
- Şartname (3 sayfa) ve yarışma e-postası incelendi; `docs/project_analysis.md` v0.1 yazıldı.
- Gereksinim taslağı `docs/requirements.md` v0.1 çıkarıldı.
- Şartnameden kabul testleri `docs/testing_strategy.md`'ye, iş listesi ve takvim `docs/development_plan.md`'ye yazıldı.
- Tespit: şartname PDF'inde Görev 2'nin atıf yaptığı "örnek görsel" yok (soru S-01).
- Kod yazılmadı; hiçbir test çalıştırılmadı.

### 24 Ekim 2026 (ikinci tur)
- Ekip cevapları belgelere işlendi: takım adı Synera; teslim adresi ext.s.a.bakir@delta-ac.de (yanıtla ile gönderilenler ulaşmıyor); ekip Go bilmiyor (Kotlin/Python); gerçek veri yok.
- Üç PDF kopyasının aynı olduğu ve hiçbirinde görsel olmadığı doğrulandı.
- Geliştirme ortamı yoklandı: bu bilgisayarda Android Studio ve SDK kurulu değil, Docker Desktop kapalı.
- `docs/technical_research.md` v0.1 yazıldı; ADR-001…007 "Önerildi" durumunda eklendi. Sürümler resmî paket depolarından okundu.
- Kod yazılmadı; hiçbir test çalıştırılmadı.

### 24 Ekim 2026 (üçüncü tur) — mimari
- ADR-001…007 ekip onayıyla "Kabul edildi".
- `docs/architecture.md` v0.1, `docs/data_model.md` v0.1, `docs/api.md` v0.1 yazıldı; ADR-008 (stok defteri) önerildi; FR-607 (bütünlük raporu) eklendi.
- Tasarım doğrulaması: `reports/design_validation/model_check.py` şartname senaryolarını sade bir modelde çalıştırdı — 20/20 kontrol geçti. Bu bir ürün testi değildir.
- Ürün kodu yazılmadı.

### 24 Ekim 2026 (dördüncü tur) — ortam kurulumu (T-05)
- ADR-008 ve mimari ekipçe onaylandı.
- `backend/`: FastAPI uygulaması, `GET /api/v1/health` (veritabanı kontrollü), ayarlar, veritabanı bağlantısı, Alembic iskeleti, Dockerfile, iki test.
- `web/`: React 19 + Vite 8 + TypeScript (strict) + Ant Design 6 + TanStack Query; "Sistem durumu" sayfası; nginx ile ters vekil; Dockerfile.
- Kök: `docker-compose.yml` (mysql:8.4, api, web), `.env.example`, `.dockerignore`, `.gitattributes`; `.gitignore` genişletildi.
- Testler çalıştırıldı ve sonuçlar `reports/test_results.md`'ye yazıldı: pytest 2/2, ruff ve oxlint temiz, uçtan uca sağlık kontrolü HTTP 200. Kurulumda bulunan 4 hata giderildi.
- Bu bilgisayarda Docker Desktop'ın açılmasını engelleyen eski soket dosyası sorunu giderildi (README → Sorun giderme).
- Android Studio kurulumu winget ile başlatıldı; lisans onayı bekleniyor.

### 24 Ekim 2026 (beşinci tur) — veritabanı şeması (T-06)
- Ekip 2 kişi olarak teyit edildi; MySQL'de kalınmasına karar verildi (şartnamede zorunlu).
- `backend/app/models/`: 31 tablonun SQLAlchemy modelleri, ortak tipler (kayan noktalı tip yok), durum değerleri; `products.default_purchase_price` eklendi (FR-101).
- İlk Alembic göçü: tablolar, adlandırılmış denetim kısıtları, `stock_movements` için UPDATE/DELETE engelleyen tetikleyiciler, senkron sayacı satırı.
- `data/seed/base.json` + `app/seed.py`: boş veritabanına örnek ana veriler; `app/security.py`: scrypt parola özeti.
- Ayrı test veritabanı (`scripts/mysql-init/01_test_db.sql`), test altyapısı; 23 test geçiyor, ruff temiz (`reports/test_results.md`).
- MySQL `--log-bin-trust-function-creators=1` ile başlatılıyor (tetikleyiciler için; ADR-008 notu).

### 24 Ekim 2026 (altıncı tur) — stok defteri ve maliyet motoru (T-07, T-08)
- `app/domain/`: yuvarlama kuralları, maliyet (EKP, kâr/marj, değerli çıkış), en büyük kalan yöntemiyle dağıtım, ağırlık dengesi, lot ağında gezinme — veritabanısız saf fonksiyonlar.
- `app/services/ledger.py`: deftere tek yazma yolu (lot/bloke/eksi stok denetimi, değerleme, özetlerin güncellenmesi, transfer, ters kayıt); `lot_graph.py`, `purchasing.py`, `numbering.py`, `integrity.py`.
- Senkronize edilen tablolara otomatik değişiklik numarası; API hata biçimi (`app/api/errors.py`).
- Örnek kayıtlara hammadde alışları eklendi: ET-2026-001, BAH-2026-014, BAG-2026-007, KUZU-2026-012 (287,50 + 63,50 = 351,00 €).
- 78 test geçiyor; çalışan sistemde 8 değişmezin hepsi tutarlı (`reports/test_results.md`).

### 24 Ekim 2026 (yedinci tur) — Android iskeleti (T-13)
- Sunucu: `POST /auth/login`, `GET /auth/me` (oturum belirteci, sunucuda yalnız özeti), `GET /sync/pull` (değişiklik numarasıyla artımlı çekme, yalnız satış rolü); istek başına tek işlem; 11 yeni test (toplam 89).
- `android/`: Gradle 9.8.2 (sağlama özetli wrapper), AGP 9.4.1, Kotlin 2.4.21, Compose, Room, Retrofit; giriş ve ana ekran; Room tabloları; para kuruş, miktar binde bir birim; 8 birim testi.
- Android 17 yerel ağ izni (`ACCESS_LOCAL_NETWORK`): yalnız sunucu yerel ağdaysa girişte istenir.
- Emülatörde uçtan uca denendi: giriş, ilk çekme (15 kayıt), araç stoku, bloke lotun cihaza inmesi.

### 24 Ekim 2026 (sekizinci tur) — Görev 1 dış üretim emri (T-09)
- Yerel git kaydı başlatıldı; uzak depo yok, GitHub'a gönderim proje bitince ve ön izlemeyle.
- `app/services/production.py`: dış üretim emri — oluşturma, girdilerin dış üretici deposuna sevki, kabul (tüketim, iade, hizmet bedeli, mamul lotu, lot bağları), iptal; maliyet, EKP/VKP/kâr/marj ve verim özeti.
- Yeni uçlar: ürün ve cari kartları, depolar, alış, lot listesi/ayrıntısı/hareketleri, transfer, üretim emirleri (`docs/api.md`).
- Hata düzeltmesi: API işlemi yanıt gönderildikten sonra kaydediyordu; hemen ardından gelen istek veriyi göremiyordu. Kayıt artık yanıttan önce; bağlantılar READ COMMITTED.
- Hata düzeltmesi: sunucu veritabanı sıfırlanınca telefon eski kayıtları tutuyordu. Çekme yanıtına veri kümesi kimliği eklendi (göç `e93069315efb`); telefon kimlik değişince yerel kopyasını baştan kurar (Room sürüm 2).
- 111 sunucu testi, 9 Android birim testi geçiyor; senaryo çalışan sistemde ve telefonda denendi (`reports/test_results.md`).

### 24 Ekim 2026 (dokuzuncu tur) — Görev 1 web ekranları (T-10)
- Web: giriş/çıkış, ürün ve cari kartları, hammadde alışı (fatura farkı açıklaması, ek maliyetler, lot değeri ön izlemesi), stok durumu, lot listesi ve ayrıntısı (hareket geçmişi, lot ağı), transferler, dış üretim emri (oluştur, sevk, kabul, iptal, EKP dökümü, kâr/marj, verim). Dar ekranda menü üst çubuktaki düğmeyle açılıyor.
- API tipleri OpenAPI tanımından üretiliyor (`docs/openapi.json`, `web/src/api/schema.d.ts`).
- Sunucu: `GET /stock`, `POST /auth/logout`; hareket geçmişinde belge numarası ve kullanıcı; zamanlar `Z` ekli UTC; dış üretici olarak kaydedilen cariye otomatik depo.
- Testler: 113 sunucu testi, 16 web birim testi (Vitest 5.0.5), 9 Android testi; senaryo tarayıcıda denendi (`reports/test_results.md`).

### 24 Ekim 2026 (onuncu tur) — Görev 2 parçalama API'si (T-11)
- `app/services/cutting.py`: reçete oluşturma ve doğrulama; parçalama taslağı, tartım, ön izleme (kaydetmeden), onay (tüketim, iki yöntemle maliyet dağıtımı, parça lotları, lot bağları).
- Uçlar: `/cutting-recipes`, `/cuttings` (`docs/api.md`).
- Sunucu mesajlarındaki sayılar Türkçe biçimde (`tr_number`): "fark 3.000 kg" yerine "fark 3 kg", "1.543,50 €".
- 126 sunucu testi; AT-03 ve AT-04 API üzerinden geçti; canlı senaryo ve bütünlük 8/8 (`reports/test_results.md`).

### 24 Ekim 2026 (on birinci tur) — Görev 2 parçalama web ekranları (T-12)
- Parçalama listesi, yeni parçalama, tartım ekranı (her ağırlık girişinde sunucudan kaydetmeden ön izleme: ağırlık dengesi, iki yöntemle pay ve €/kg), onay ve sonuç (dağıtım dökümü, parça lotları), reçete listesi ve yeni reçete.
- Lot sayfasında parçalama belgelerine bağlantı; dar ekranda menü sayfa açılışında kapalı başlıyor.
- Senaryo tarayıcıda baştan sona denendi (`reports/test_results.md`).

### 24 Ekim 2026 (on ikinci tur) — Android satış ve gönderim (T-14, T-15)
- Sunucu: `POST /sync/push` (UUID ile tekrar güvenli, satış başına alt işlem, çevrimdışı bloke lot satışında ihlal uyarısı), `GET /sales`.
- Android: satış ekranı (müşteri, ilk biten önerili lot listesi, miktar ve fiyat, bloke lot engeli), cihazda tek işlemde kayıt (Room sürüm 3), kullanılabilir miktar = sunucu bakiyesi − bekleyen satışlar, son satışlar ve durumları, WorkManager 2.12.0 ile arka planda gönderim.
- 134 sunucu testi (AT-11, AT-12 dahil), 17 Android birim testi; emülatörde bağlantılı ve uçak modunda satış denendi (`reports/test_results.md`).

### 27 Ekim 2026 — iki kişilik iş bölümü
- `docs/is_bolumu.md`: bütün gereksinimlerin kapsamı (biten / kısmen / eksik ve sahibi), dosya sahipliği, YZ kulvarıyla sunucu arasındaki sözleşme, git paketiyle günlük birleştirme, "bitti" tanımı, 1 Kasım'a kadar takvim.
- README, `android/README.md`, `ml/README.md` ve geliştirme planındaki rol tablosu bugünkü duruma getirildi.
- `scripts/api_tipleri_yenile.sh`: API tanımını (`docs/openapi.json`) ve web tiplerini tek komutla yeniler.
- Web geliştirme sunucusu API portunu `API_PORT` değişkeninden okuyor (8000 doluysa).
- Testler yeniden çalıştırıldı: 134 sunucu, 16 web, 17 Android — hepsi geçti.
- Düzeltme: `docs/openapi.json` ve web tiplerinde bozuk Türkçe karakterler (yanlış kodlamayla üretilmişti) doğru UTF-8 ile yeniden üretildi; yenileme betiği Node.js ile yazıldı.
- Ekip paketi temiz kopyada sıfırdan kurulup denendi: 134 sunucu, 16 web, 17 Android testi, APK (`reports/test_results.md`).

### 27 Ekim 2026 (ikinci tur) — Görev 3, raporlar, yapay zekâ, 3D arayüz
- İş bölümü teknik kulvarlara göre yeniden yazıldı (`docs/is_bolumu.md`): Kişi 1 sunucu, web, yapay zekâ; Kişi 2 Android, eşitleme ve teslim. Depo adı önerisi: `synera-avatar`.
- Görev 3 sunucu: ileri/geri izleme (`/trace`), geri çağırma (başlat, liste, CSV iletişim listesi, kapat: imha/serbest), uyarılar, ikinci kademe teslimat (kesin / kısmen / bilinmiyor), müşteri iadesi, fire/imha, ters kayıt.
- Demo profili (varsayılan): kurulumdan sonra ET-2026-001 → URT-2026-045 → SUC-2026-045 → Market A 30 / B 25 / C 30 ve örnek parçalama hazır (FR-309).
- Göç: iade ve fire kaydının hareket bağı, kayıt ve hareket aynı işlemde yazılabilsin diye boş geçilebilir oldu.
- Raporlar (`/reports`): alış, üretim, parçalama, lot hareketleri, satış, geri çağırma, bütünlük; süzgeç ve CSV.
- Yapay zekâ: sabit tohumlu sentetik veri, Model A (et bazlı verim → paket ve EKP) ve Model B (parça payları); kronolojik %80/%20, zaman sıralı çapraz doğrulama, referans yöntemle karşılaştırma. Tahmin iş anında kaydediliyor; model yoksa iş akışı durmuyor. Rapor: `reports/ai_degerlendirme.md`.
- Web: izleme, geri çağırma, uyarı, satış/iade, rapor ve yapay zekâ ekranları; lotta fire ve ters kayıt; üretim emrinde tahmin kartı; derinlikli (3D) tasarım.
- Android: marka renkleri, derinlikli kartlar (dokununca eğilme), üst bant ve gösterge kutuları, geri çağrılan lot için açıklamalı kırmızı kart.
- Belgeler: `docs/senkronizasyon.md`, `reports/gorev2_tutarsizliklar.md`, README'de beş dakikalık senaryo.
- Testler: 166 sunucu, 4 yapay zekâ, 16 web, 17 Android — hepsi geçti (`reports/test_results.md`).

### 27 Ekim 2026 (üçüncü tur) — yeniden işleme, kabul testleri, teslim hazırlığı
- Yeniden işleme (FR-303): `POST/GET /reprocessing` ve web ekranı. Girdi lotları tüketilir, yeni lot girdilerine bağlanır, değer = girdiler + ek maliyet.
- Kabul testleri AT-01…AT-15 çalışan sisteme karşı: `tests/`, `scripts/kabul_testleri.sh` (ayrı kopyada sıfırdan kurulum). Sonuç 23/23, izleme 0,043 sn (`reports/kabul_testleri.md`).
- Paketten temiz kurulum provası: sunucu 170, yapay zekâ 4, kabul 23, web 16, Android 17 — hepsi geçti; APK üretildi.
- README: test komutları, bilinen sınırlamalar, APK; `docs/data_model.md` v0.3; teslim kontrol listesi güncellendi.

### 28 Ekim 2026 — denetim düzeltmeleri, gerçek kullanım, yeni arayüz, dil seçeneği
- Denetim (27 Ekim) düzeltmeleri: aynı tedarikçi faturası iki kez girilemez; var olmayan depo 404; iade müşterinin dağıttığı miktarı aşamaz (satır kilitli); geri çağırma başlatırken lot kilitlenir; lotu olan ürünün birimi değişmez; şube döngüsü engellenir; tarihler işletmenin yerel gününe göre (UTC+3); veritabanı çakışması 409, beklenmeyen hata 500 (ayrıntı sızmaz); CSV'de formül hücresi düz metin; sevk edilmiş fason emri iptal edilince hammadde ana depoya döner; web'de Türkçe büyük harf hatası (sirt → SİRT) giderildi; geçersiz sayfa kimliği "bulunamadı"; sayfalar ayrı yüklenir; nginx güvenlik başlıkları ve sıkıştırma; Android'de çıkışta sunucu oturumu kapanır, sıfırlanmış sunucuya eski satış gönderilmez, uygulama verisi yedeğe alınmaz.
- Roller: yönetici, depo, üretim, kalite, mağaza, satış; her uç işi yapan role açık. Kullanıcı yönetimi, şifre değiştirme, ilk girişte şifre belirleme, hatalı giriş sınırı.
- Gerçek kullanım: mağaza satışı (ödeme türü, liste fiyatı, ilk dolan ilk çıkar), son kullanma kuralı (mağazada satılamaz; telefonda çevrimdışı satılırsa uyarı), gün sonu, depo/araç sayımı, ana sayfa özeti, kritik stok, "Perakende müşteri". Göç `b2d9f1c4e7a3` (33 tablo).
- Web baştan tasarlandı: sade görünüm, işe göre menü, rol bazlı ana sayfa ("bugün yapılacaklar"), sade terimler (fason üretim, birim maliyet, satışa kapalı, geri al), yeni ekranlar (mağaza satışı, gün sonu, son kullanma, sayım, kullanıcılar, şifre, geri çağırma tatbikatı), yazdırılabilir belgeler (Code 128 barkodlu lot etiketi, fiş/irsaliye, geri çağırma bildirimi, gün sonu, sayım tutanağı, tatbikat raporu).
- Android baştan tasarlandı: alt menü (Satış, Stok, Geçmiş, Gün sonu), dört adımlı satış, otomatik lot seçimi, ödeme türü (Room v4), gün sonu ve araç sayımı.
- Dil seçeneği: web ve telefon Türkçe / English; sayı ve tarih biçimi dile göre; testler her metnin çevirisini denetler.
- Testler: 215 sunucu, 4 yapay zekâ, 23 kabul (sıfırdan kurulum), 26 web, 22 Android — hepsi geçti (`reports/test_results.md`).

### 28 Ekim 2026 (ikinci tur) — alarm merkezi, denetim günlüğü, e-posta, panel, hesaplayıcılar, turkuaz + 3B
- Alarm kural motoru: verim sapması (gerçek verimin model beklentisinden sapması, z-skoru; σ modelin test hatasından), alış fiyatı artışı (bir önceki alışa göre %), bloke lotta stok. Olay alarmları: geri çağırma başladı, mağazada bloke lot satış denemesi (satış reddedilir), çevrimdışı geri çağırma/SKT ihlali, art arda hatalı giriş. Her durum için tek alarm; kurallar girişte, ilgili kayıttan sonra ve yöneticinin düğmesiyle çalışır; eşikler yönetimden değişir.
- Denetim günlüğü: kim, ne zaman, ne yaptı (giriş, hatalı giriş, mal kabul, üretim, parçalama, satış, iade, fire, transfer, sayım, geri çağırma, kullanıcı, ayar, e-posta, alarm); önem derecesi, arama, süzme, CSV. Hatalı girişler hata yanıtına rağmen kalıcı yazılır.
- E-posta giden kutusu: kritik alarm yönetici ve kaliteye, uyarı yöneticiye. `.env`'de SMTP tanımlıysa arka planda gönderilir, değilse "Kuyrukta" bekler. Rapor e-postası (günlük özet, maliyet ve sevkiyat, geri çağırma bildirimi — her müşteriye yalnız kendi miktarı —, açık alarmlar) ön izlemeli; e-posta programında açma seçeneği.
- Panel grafikleri: EKP gerçek ve model tahmini (sistemde az emir varken modelin sentetik test verisi ayrıca, etiketli), hedef/gerçekleşen, maliyet halkası, izometrik 3B parça maliyeti, müşteri sevkiyatı, açık alarmlar; her grafikte tablo görünümü.
- "Ne olur" hesaplayıcıları: EKP (fatura/teslim adedi farkı, hizmet faturası farkı, kâr ve marj) ve parçalama (değere/kiloya göre dağıtım, fire, ağırlık dengesi, fatura–tartım farkı). Gerçek kayıtla aynı maliyet fonksiyonları kullanılır.
- Faturadan doldur: fatura/irsaliye metninden tedarikçi, belge no, tarih ve satırlar (ürün, miktar, lot, fiyat, SKT) önerilir; kaydetmez, kullanıcı kontrol edip kaydeder. Lot numarası bulunamazsa uydurulmaz.
- Görünüm: turkuaz geçişli menü, buzlu cam kartlar, fareyle eğilen 3B kartlar, izometrik 3B sütunlar; azaltılmış hareket tercihinde kapanır. Android üst çubuğu da turkuaz.
- Kullanıcılara e-posta alanı. Göç `c5e8a1f0d2b6` (36 tablo: `audit_events`, `app_settings`, `mail_outbox`).
- Testler: 237 sunucu, 30 web, 22 Android (`reports/test_results.md`).

### 28 Ekim 2026 (üçüncü tur) — e-posta bildirimleri
- Mailer modülü (`app/mailer.py`, yalnız standart kütüphane): HTML + düz metin, tek ek, STARTTLS + giriş yalnız SMTP_USER doluysa; hata günlüğe yazılır, API düşmez; sonuç giden kutusunda.
- Gerçek zamanlı gönderim: giden kutusuna yazan işlem kaydedilince gönderici hemen uyanır; başarısızsa yeniden dener.
- `POST /api/v1/reports/{kod}/email` (202): rapor CSV ekiyle; alıcı yalnız aktif kullanıcı ya da `ALLOWED_EMAIL_DOMAINS`, aksi 422; kullanıcı başına dakikada 5; denetim günlüğü.
- Alarm e-postası abonelere (`alert_subscriptions`, rol varsayılanları), her alıcıya ayrı, aynı alarm aynı adrese bir kez; konu `[AVATAR UYARI] <başlık>`, gövdede lot/ürün ve web bağlantısı. Uçlar `GET/PUT /api/v1/alerts/subscriptions`.
- Yeni uyarılar: SKT yaklaşan/geçen lot, sayım farkı. Göç `d7f3b9a2c4e1` (37 tablo).
- docker-compose'a Mailpit (`axllent/mailpit:v1.32.0`, 8025 arayüz, 1025 SMTP); `.env.example` yeni değişkenlerle. Değişken adları `SMTP_PASS`, `MAIL_FROM` (eski `SMTP_PASSWORD`, `SMTP_FROM` de okunur).

### 31 Ekim 2026 (ikinci tur) — Ayarlar (web ve telefon)
- Web: **Ayarlar** sayfası (`/ayarlar`, herkese):
  - Hesabım ve Dil bölümleri.
  - Güvenlik: şifre, açık oturumlar, diğer cihazlardan çıkış.
  - Kişiye özel e-posta bildirim tercihleri: sunucuda vardı, ekranı yoktu.
  - Hakkında ve yardım: sürüm, durum, kişisel veriler.
  - Yöneticiye "İşletme ayarları" bölümü.
- Sunucu: `GET /auth/sessions`, `POST /auth/sessions/close-others`; denetim kaydı `OTURUMLAR_KAPATILDI`.
- Telefon: **Ayarlar** ekranı. Hesap, şifre değiştirme, eşitleme durumu, dil, sürüm, cihaz kimliği ve onaylı çıkış.
- Hata düzeltmesi (telefon): geçici şifreli satış elemanı hiç çalışamıyordu.
  - Durum: Yöneticinin açtığı ya da şifresini sıfırladığı satış elemanı, sunucu "önce şifre değiştir" dediği için eşitleyemiyordu.
  - Neden: Web satış elemanına kapalı, telefonda da şifre ekranı yoktu.
  - Çözüm: Telefon artık geçici şifreyle girişte zorunlu yeni şifre ekranını açar. Şifre kuralı telefonda da denetlenir (`PasswordRules`).
- Alarm türlerinin "ne zaman" açıklamaları ortak listede (`ALERT_WHEN`).

### 31 Ekim 2026 — uçtan uca güvenlik denetimi
- Rapor: `docs/guvenlik/guvenlik_denetimi.md` (20 temel kontrol + mobil, web, API, e-posta, Docker/CI; düzeltilenler; kalan riskler; video bölümü; son karar).
- API ve Mailpit portları yalnız `127.0.0.1`'e bağlanır (önce bütün ağa açıktı); telefon web portunu (nginx) kullanır. `API_BIND` ayarı.
- Demo dışı kurulumda örnek kullanıcı şifreleri geçici; ilk yönetici için `python -m app.create_admin` (tek kullanımlık şifre).
- API yanıtlarında `Cache-Control: no-store`.
- Bütün API'nin yetki matrisi koddan üretilir (`app/access_matrix.py`, `docs/guvenlik/api_yetki_matrisi.md`); 95 uç (Ayarlar turunda 97) girişsiz ve her yetkisiz rolle sınanır (yetki hatası bulunmadı).
- Android: oturum belirteci Keystore + AES-GCM ile şifreli (eski düz belirteç taşınıp silinir); şifresiz HTTP yalnız debug derlemesinde.
- Web: rol dışı yönetici ekranına adresle gidilince "Bu ekrana yetkiniz yok" sayfası.
- Yedekleme: `scripts/yedekle.sh`, `scripts/geri_yukle.sh` (onaylı), `scripts/yedek_denemesi.sh` (ayrı veritabanına geri yükleyip karşılaştırır).
- Canlı güvenlik denemesi: `scripts/guvenlik_denemesi.sh` (27 saldırı isteği, nginx üzerinden).
- CI: `.github/workflows/ci.yml` (ruff, pytest + MySQL, yapay zekâ, pip-audit, web lint/test/derleme, npm audit, Android test + APK, gitleaks); eylemler commit SHA'sıyla sabit. GitHub'da henüz çalışmadı.
- Düzeltme: 4 test sabit tarih yüzünden 31 Ekim'de düşüyordu; bugünün tarihine bağlandı.

### 29 Ekim 2026 — serbest e-postada açık röle kapatıldı
- `POST /api/v1/mail`: alıcı yalnız aktif kullanıcı, kayıtlı cari (müşteri, tedarikçi, dış üretici) e-postası ya da `ALLOWED_EMAIL_DOMAINS`; başka adres 422 (önce her adrese gidebiliyordu).
- Kullanıcı başına dakikada 5 gönderim sınırı serbest e-postada da; rapor e-postasıyla ortak sayaç.
- `POST /api/v1/mail/batch`: ayrı ayrı e-postalar tek gönderim (web'de müşterilere geri çağırma bildirimi artık tek istekte; beşten fazla müşteride sınıra takılmaz, biri geçersizse hiçbiri yazılmaz).
- Alıcı kuralı ve sınır ortak modülde (`app/services/mail_policy.py`).
