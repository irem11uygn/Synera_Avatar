# Test Sonuçları

Kural (`docs/testing_strategy.md`): yalnızca gerçekten çalıştırılan testler yazılır; her kayıtta tarih, komut ve sonuç bulunur.

## 24 Ekim 2026 — T-05 ortam kurulumu (iskelet)

Ortam: Windows 11, Docker 29.8.2 (Docker Desktop 4.94.0), `docker compose up --build -d` ile `db` (mysql:8.4 → 8.4.13), `api`, `web`.

| Kontrol | Komut | Sonuç |
|---|---|---|
| Sunucu birim/entegrasyon testleri | `docker compose run --rm --no-deps api pytest -v` | **2 geçti**, 0 kaldı, uyarı yok (`test_health_reports_database_ok` gerçek MySQL'e bağlanır; `test_health_reports_degraded_when_database_unreachable` veritabanı hatasını taklit eder) |
| Python kod denetimi | `docker compose run --rm --no-deps api sh -c "ruff check . && ruff format --check ."` | Sorun yok; 10 dosya biçimli |
| Web tip denetimi + derleme | `cd web && npm run build` | Başarılı. Uyarı: ana paket 630 kB (antd); sayfalar eklenince parçalara bölünecek |
| Web kod denetimi | `cd web && npx oxlint` | Çıkış kodu 0 |
| API sağlık ucu | `curl http://localhost:8000/api/v1/health` | HTTP 200 `{"status":"ok","database":"ok","version":"0.1.0"}` |
| Web → API ters vekil | `curl http://localhost:8080/api/v1/health` | HTTP 200, aynı gövde |
| Tek sayfa uygulama yönlendirmesi | `curl http://localhost:8080/lotlar` | HTTP 200 (index.html) |
| Vite geliştirme sunucusu vekili | `npx vite` + `curl http://localhost:5173/api/v1/health` | HTTP 200 |
| OpenAPI | `curl http://localhost:8000/openapi.json` | "AVATAR — Synera 0.1.0", yol: `/api/v1/health` |
| MySQL ayarları | `SELECT VERSION(), @@character_set_server, @@collation_server` | 8.4.13, utf8mb4, utf8mb4_0900_ai_ci; Alembic tablosu oluştu |
| Tarayıcı | http://localhost:8080 | "Sistem durumu" kartında API ve veritabanı "Çalışıyor"; konsolda hata yok |

Yolda bulunan ve düzeltilen hatalar:

1. API konteyneri açılışta kapanıyordu: `alembic` komutu çalışma dizinini içe aktarma yoluna eklemediği için `migrations/env.py` `app` paketini bulamıyordu → `alembic.ini`'ye `prepend_sys_path = .` eklendi.
2. pytest `app` paketini bulamıyordu → `pyproject.toml`'a `pythonpath = ["."]`.
3. Konteynerde kod dizini bilerek salt okunur; pytest ve ruff önbellekleri yazamıyordu → önbellekler `/tmp`'ye yönlendirildi (`RUFF_CACHE_DIR`, `PYTEST_ADDOPTS`).
4. Starlette 1.9 test istemcisi `httpx` için kullanım dışı uyarısı veriyordu → aynı yazarın yeni paketi `httpx2` (github.com/pydantic/httpx2) kullanıldı.

## 24 Ekim 2026 — T-06 veritabanı şeması ve örnek kayıtlar

Ortam aynı; testler ayrı `avatar_test` veritabanında, şema her test oturumunda sıfırdan kurularak çalıştı.

| Kontrol | Komut | Sonuç |
|---|---|---|
| Sunucu testleri | `docker compose run --rm --no-deps api pytest -v` | **23 geçti**, 0 kaldı, uyarı yok |
| Python kod denetimi | `… api sh -c "ruff check . && ruff format --check ."` | Sorun yok; 30 dosya biçimli |
| Açılış (temiz veritabanı) | `docker compose down -v && docker compose up --build -d` | Göç `df3690a4b5d8` uygulandı; "'base' profili yüklendi: 10 ürün, 10 cari" |
| Açılış (dolu veritabanı) | `docker compose up -d --force-recreate api` | "Veritabanı boş değil; örnek kayıtlar yüklenmedi" |
| Geliştirme veritabanında tetikleyiciler | `information_schema.triggers` | `stock_movements_no_update`, `stock_movements_no_delete` |
| Web → API | `curl http://localhost:8080/api/v1/health` | HTTP 200 |

Testlerin doğruladıkları:

| Test dosyası | Doğrulanan | Gereksinim |
|---|---|---|
| `test_schema.py` | 31 tablonun hepsi oluşuyor; modeller ile göç arasında fark yok (`alembic check`); stok hareketi güncellenemez ve silinemez; sıfır miktarlı hareket ve eksi bakiye reddediliyor; lot numarası tekil; 25 × 11,50 = 287,50 ≠ 351,00 olan alış satırı açıklamasız reddediliyor, açıklamayla kabul ediliyor; senkron sayacı tek satır | NFR-002, NFR-004, FR-102, FR-207, AT-05 (veritabanı düzeyi), AT-10 (kısmen) |
| `test_seed.py` | Narin Sucuk 1 kg paket, VKP 24,90; hammadde fiyatları 9,70 / 24,00 / 11,60; Market A/B/C + Market B'nin 2 şubesi ve iletişim bilgileri; kuzu reçetesi oranları toplamı 1, fireye maliyet yok, tolerans 0,2 kg; demo kullanıcıları ve araç deposu; ilk üretim emri numarasının 045 olacağı; örnek kayıtların ikinci kez yüklenmemesi | FR-101, FR-103, FR-201, FR-202, FR-301 |
| `test_security.py` | Parola özeti doğru/yanlış parola, tuz, bozuk özet | NFR-007 |

Yolda bulunan ve düzeltilen hatalar:

1. Tetikleyici oluşturma "hata 1419" ile reddedildi: MySQL'de ikili günlük açıkken yönetici olmayan kullanıcı tetikleyici oluşturamıyor → MySQL `--log-bin-trust-function-creators=1` ile başlatılıyor (ADR-008'e not düşüldü). MySQL şema değişikliklerini geri alamadığından yarım kalan şema `docker compose down -v` ile temizlendi; birimde örnek veri dışında bir şey yoktu.
2. Otomatik üretilen göçte ve modelde 110 karakteri aşan bir kısıt satırı → bölündü.
3. Alembic `path_separator` kullanım dışı uyarısı → `alembic.ini`'ye `path_separator = os` eklendi.
4. Veri modelinde FR-101'in istediği "varsayılan alış fiyatı" sütunu eksikti → `products.default_purchase_price` eklendi, `data_model.md` güncellendi.

## 24 Ekim 2026 — T-07 stok defteri ve lot ağı, T-08 maliyet motoru

| Kontrol | Komut | Sonuç |
|---|---|---|
| Sunucu testleri | `docker compose run --rm --no-deps api pytest -q` | **78 geçti**, 0 kaldı, uyarı yok |
| Python kod denetimi | `… api sh -c "ruff check . && ruff format --check ."` | Sorun yok; 52 dosya biçimli |
| Açılış (temiz veritabanı) | `docker compose down -v && docker compose up --build -d` | "'base' profili yüklendi: 10 ürün, 10 cari, 4 alış" |
| Çalışan sistemde bütünlük denetimi | `check_invariants` (I-1…I-8) | 8/8 tutarlı; ET-2026-001 100 kg / 970,00 €, BAH-2026-014 2 kg / 48,00 €, BAG-2026-007 5 kg / 58,00 €, KUZU-2026-012 25 kg / 351,00 € |

Testlerin doğruladıkları (yeni):

| Test dosyası | Doğrulanan | Kabul testi |
|---|---|---|
| `test_costing.py` | Hammadde 970,00 + 48,00 + 58,00, hizmet 467,50, toplam 1.543,50, EKP 18,158824 → 18,16; 18,16 × 85 = 1.543,60 olduğu için lot değerinin toplamdan tutulması; VKP 24,90'da brüt kâr 6,74 ve marj %27,07; 84 paket gelirse EKP 18,31; 30/25/30 satış maliyetleri 544,76 + 453,97 + 544,77 = 1.543,50 | AT-01, AT-02 |
| `test_allocation.py` | Miktar ağırlıklı 111,68 / 63,82 / 79,77 / 47,87 / 47,86 ve değer ağırlıklı 123,41 / 83,34 / 72,12 / 33,66 / 38,47 (ikisi de 351,00); düz yuvarlamanın 350,99 vereceği; fireye ve maliyet taşımayan yan ürüne pay verilmemesi; 500 rastgele durumda toplamın korunması | AT-03 |
| `test_balance_and_graph.py` | 25 kg giriş / 22 kg parça → 3 kg fark, fire girilince denge; tolerans; çoktan çoğa ağda derinlikli gezinme; döngüde sonlanma | AT-04, AT-06/07 (gezinme) |
| `test_ledger.py` | Alış girişi; şartname zinciri (sevk → tüketim → SUC-2026-045 = 1.543,50 € → araç deposu); transferin değer taşımaması; satışların lot değerini tam tüketmesi; fazla satışın reddi ve hiçbir şey yazılmaması; satışın yalnız malın bulunduğu depodan yapılabilmesi; bloke lotta satış/transferin reddi, çevrimdışı Android satışının istisnası, imhanın serbest olması; ET-2026-001 → SUC-2026-045 ileri ve geri izleme; ters kaydın lotu tam geri getirmesi ve ikinci kez yapılamaması; değişiklik numaralarının artması; senaryo sonunda bütün değişmezlerin tutması | AT-01, AT-06, AT-07, AT-08, AT-10 |
| `test_purchasing.py` | 25 × 11,50 = 287,50 ≠ 351,00 → açıklamasız red (hiçbir şey yazılmadan), açıklamalı kabul; 287,50 + kesim 40,00 + nakliye 23,50 = 351,00; son tüketim tarihinin raf ömründen hesaplanması; yalnız tedarikçiden alış; tekrar eden lot numarasının reddi | AT-05 |
| `test_integrity.py` | Örnek verilerde 8 değişmezin tutması; defteri atlayan bir yazımın I-1, I-2, I-3 ile yakalanması | AT-10 |
| `test_numbering.py` | Sıradaki belgeler URT-2026-045, PRC-2026-012, SAT-2026-0101 | — |
| `test_errors.py` | Hata yanıtı biçimi (`api.md` §3), ondalıkların metin taşınması, istek doğrulama hatası | — |

Yolda bulunan ve düzeltilen hatalar:

1. T-06'dan kalan üç şema testi, artık örnek kayıtlarda bulunan `ET-2026-001` ve `KUZU-2026-012` lot numaralarını kullanıyordu → testlere kendi lot numaraları verildi (ürün hatası değil, test verisi çakışması).
2. İki satır 110 karakter sınırını aşıyordu → bölündü.

Henüz test edilmeyen: iki ayrı bağlantıdan aynı anda aynı stoğun satılması (satır kilidinin eşzamanlı davranışı) — T-23'te.

## 24 Ekim 2026 — T-13 Android iskeleti (+ giriş ve çekme uçları)

| Kontrol | Komut | Sonuç |
|---|---|---|
| Sunucu testleri | `docker compose run --rm --no-deps api pytest -q` | **89 geçti** (11 yeni: giriş, oturum, çekme senkronu) |
| Python kod denetimi | `… ruff check . && ruff format --check .` | Sorun yok; 59 dosya biçimli |
| Android derleme | `./gradlew assembleDebug` (Gradle 9.8.2, AGP 9.4.1, JDK 25 — Android Studio) | Başarılı; debug APK 12,8 MB |
| Android birim testleri | `./gradlew testDebugUnitTest` | **8 geçti**, 0 kaldı (UnitsTest 5, PullMappingTest 1, LocalNetworkTest 2) |
| Kotlin derleyicisi | `:app:dependencies --configuration kotlinCompilerClasspath` | kotlin-compiler-embeddable 2.4.21 |
| Emülatörde uçtan uca | Medium_Phone AVD, Android 17 (API 37); APK `adb install` | Aşağıda |

Emülatörde elle (adb ile) yapılan uçtan uca deneme:

1. Uygulama açıldı; giriş ekranı Türkçe karakterlerle doğru çizildi, sunucu adresi `http://10.0.2.2:8000` geldi.
2. Boş alanla giriş: "Kullanıcı adı ve parola gerekli." uyarısı.
3. Yerel ağ izni olmadan: "Sunucuya ulaşılamadı…" (aşağıdaki hata 2).
4. Giriş → Android'in "Yakındaki cihazlar" izin penceresi → izin verildi → `POST /auth/login 200`, ardından `GET /sync/pull?since=0 200`.
5. Ana ekran: "10 ürün · 3 müşteri · 1 lot araçta", "15 kayıt güncellendi" (10 ürün + 3 müşteri + 1 lot + 1 stok satırı); araç stokunda "Sucukluk et · Lot ET-2026-001 · SKT 31.10.2026 · 10 kg" (deneme için sunucuda 10 kg araca transfer edildi).
6. Sunucuda ET-2026-001 bloke edildi → "Verileri güncelle" → `GET /sync/pull?since=26` → "1 kayıt güncellendi", lot satırında kırmızı "BLOKE — satılamaz".
7. Deneme bitince geliştirme veritabanı temiz örnek kayıtlara döndürüldü (`docker compose down -v` + `up`).

Yolda bulunan ve düzeltilen hatalar:

1. `local.properties`'te SDK yolu tek ters bölüyle yazılmıştı; bu dosya biçiminde `\` kaçış karakteri olduğu için yol bozuldu ("Invalid file path") → ileri bölüyle yazıldı.
2. **Android 17 yerel ağ koruması:** targetSdk 37'de uygulama 10.0.2.2'ye bağlanamıyordu (`SocketTimeoutException … after 10000ms`); emülatörün kendi kabuğundan aynı port cevap veriyordu. Resmî belgeye göre targetSdk 37 uygulamaları yerel ağa `ACCESS_LOCAL_NETWORK` çalışma anı izni olmadan erişemez → izin manifeste eklendi, yalnız sunucu yerel ağdaysa girişte isteniyor.
3. Ağ hataları ayrıntısız yutuluyordu → `ApiClient` artık hatayı yığın iziyle günlüğe yazıyor.
4. Çalışan API konteyneri giriş uçları eklenmeden önceki imajla çalışıyordu → yeniden derlenip başlatıldı.
5. AGP proje yolundaki ASCII dışı karakter ("Yeni klasör") yüzünden derlemeyi durduruyordu → `android.overridePathCheck=true` (ASCII yolda etkisiz).

Test otomasyonu notları (uygulama hatası değil): emülatörde adb ile yazarken Gboard'un kalem eğitimi açıldı ve yanlış koordinatlara dokunuldu; arayüz ağacından konum bulan küçük bir yardımcıyla çözüldü. İzin penceresi, üstünde başka bir pencere varken dokunmaları yok saydığı için "İzin ver" klavyeyle seçildi.
