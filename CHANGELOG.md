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
