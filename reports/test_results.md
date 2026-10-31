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

## 24 Ekim 2026 — T-09 Görev 1 dış üretim emri (+ ana veri, alış, lot, transfer uçları)

| Kontrol | Komut | Sonuç |
|---|---|---|
| Sunucu testleri | `docker compose run --rm --no-deps api pytest -q` | **111 geçti** (22 yeni: dış üretim 12, ana veri/alış/lot/transfer 9, senkron veri kümesi kimliği 1) |
| Python kod denetimi | `… ruff check . && ruff format --check .` | Sorun yok; 71 dosya biçimli |
| Şema göçü | API açılışında `alembic upgrade head` | Dolu geliştirme veritabanında `df3690a4b5d8 → e93069315efb` uygulandı; var olan sayaç satırına UUID verildi |
| Android birim testleri | `./gradlew testDebugUnitTest` | **9 geçti**, 0 kaldı (UnitsTest 5, PullMappingTest 2, LocalNetworkTest 2) |
| Android derleme | `./gradlew assembleDebug` | Başarılı (Room veritabanı sürüm 2, göç 1 → 2) |
| Canlı senaryo | Çalışan sistemde gerçek HTTP istekleriyle (deneme betiği, depoda değil) | Aşağıda |

Canlı senaryo (`docker compose up` ile çalışan sistem, yönetici hesabı):

1. Emir: `POST /production-orders` → HTTP 201, **URT-2026-045** (TASLAK); girdiler ET-2026-001 100 kg, BAH-2026-014 2 kg, BAG-2026-007 5 kg.
2. Sevk: HTTP 200 → SEVK_EDILDI; girdiler ana depodan dış üretici deposuna transfer edildi.
3. Kabul: HTTP 200 → TAMAMLANDI, mamul lotu **SUC-2026-045**. Maliyet: hammadde 1.076,00 + hizmet 467,50 = **1.543,50 €**; EKP 18,158824 → **18,16 €**; VKP 24,90 € ile brüt kâr **6,74 €**, marj **%27,07**; verim et bazlı %85,00, toplam girdi %79,44.
4. Lot SUC-2026-045: 85 adet, 1.543,50 €, SKT 23.12.2026; kaynakları ET-2026-001 100, BAH-2026-014 2, BAG-2026-007 5.
5. Araca yükleme: `POST /transfers` → HTTP 201, TRF-2026-0002 (85 adet).
6. Bütünlük denetimi: 8/8 değişmez tutarlı.
7. Telefon (emülatör, Android 17): "Verileri güncelle" → araç stokunda "Narin Sucuk 1 kg · Lot SUC-2026-045 · SKT 23.12.2026 · 85 adet".

Geliştirme veritabanında bu senaryonun sonuçları duruyor (temiz örnek kayıtlar için `docker compose down -v` + `up`).

Yolda bulunan ve düzeltilen hatalar:

1. **Kayıt yanıttan sonra yapılıyordu.** Senaryo betiğinde girişten hemen sonraki istek ara ara 401 aldı; sevkten hemen sonraki kabul, sevk edilen miktarı 0 gördü. Neden: FastAPI'de `yield` bağımlılığının kapanış kodu (commit) varsayılan olarak yanıt gönderildikten sonra çalışıyor; istemci "başarılı" yanıtını veri kaydedilmeden alıyordu. Düzeltme: `Depends(get_db, scope="function")` ile kayıt yanıt gönderilmeden yapılıyor; bağlantılar READ COMMITTED yalıtımıyla açılıyor (`architecture.md` §7, ADR-008 notu). Doğrulama: 30 kez "giriş + hemen istek" denemesi 30/30 başarılı; senaryo baştan sona geçti.
2. **Sunucu sıfırlanınca telefon eski kayıtları tutuyordu.** Geliştirme veritabanı sıfırdan kurulduktan sonra telefon eski değişiklik numarasıyla (since=27) çekmeye devam etti; sunucuda artık olmayan "ET-2026-001 · 10 kg · BLOKE" satırı araç stokunda kaldı. Düzeltme: `sync_counter.dataset_id` (şema kurulurken UUID, göç `e93069315efb`) her çekme yanıtında gönderiliyor. Telefon kimliği değişmiş görürse ya da sunucunun numarası kendininkinden küçükse tam kopyayı çekip yerel kopyayı tek işlemde değiştiriyor (Room sürüm 2, göç 1 → 2). Doğrulama (emülatörde):
   - Yeni APK eski veritabanının üzerine kuruldu; göç 1 → 2 hatasız çalıştı.
   - Sunucu `docker compose down -v` + `up` ile sıfırlandı (kimlik `9fdc1300…` → `16d30143…`, sayaç 41 → 23). Telefon: eski oturum 401 → giriş ekranı → yeniden giriş. Sunucu kayıtlarında sırasıyla `GET /sync/pull?since=41` ve `GET /sync/pull?since=0`; ekranda "0 lot araçta", eski SUC-2026-045 satırı silindi.
   - Senaryo yeniden çalıştırıldı → "Verileri güncelle" → `GET /sync/pull?since=23` (artımlı, tam çekme yok), "2 kayıt güncellendi", SUC-2026-045 · 85 adet göründü.

## 24 Ekim 2026 — T-10 Görev 1 web ekranları

| Kontrol | Komut | Sonuç |
|---|---|---|
| Sunucu testleri | `docker compose run --rm --no-deps api pytest -q` | **113 geçti** (2 yeni: çıkış ucu, dış üreticiye otomatik depo; 2 test genişletildi: hareketlerde belge no/kullanıcı/UTC eki, `/stock`) |
| Python kod denetimi | `… ruff check . && ruff format --check .` | Sorun yok; 73 dosya biçimli |
| Web tip denetimi | `npx tsc -p tsconfig.app.json --noEmit` | Hata yok (TypeScript strict) |
| Web kod denetimi | `npx oxlint` | Uyarı yok |
| Web birim testleri | `npm test` (Vitest 5.0.5) | **16 geçti**: ondalık hesap 6, biçimler 5, kullanıcı girişi 2, yol eşleme 3 |
| Web derleme | `npm run build` / `docker compose up -d --build web` | Başarılı; paket 1,2 MB (sıkıştırılmış 378 kB), Vite boyut uyarısı veriyor (ADR-002 notu) |
| Bütünlük (çalışan sistem) | `check_invariants` | Arayüz senaryosundan sonra 8/8 tutarlı |

Tarayıcıda elle denenen senaryo (geliştirme sunucusu 5180 ve Docker'daki nginx 8080; masaüstü 1280 px ve telefon 375 px):

1. Giriş: demo yönetici ile giriş; sayfa yenilenince oturum sürüyor. Satış kullanıcısı Türkçe uyarıyla reddedildi.
2. Hammadde alışı: FAT-ET-2026-0500, ET-2026-002, 50 kg. Birim fiyat (9,70 €) ve SKT (belge tarihi + 7 gün = 31.10.2026) üründen otomatik geldi. Ön izleme 485,00 € gösterdi. Fatura 490,00 € girilip açıklama boş bırakılınca kayıt engellendi. Açıklama yazılınca kaydedildi; lot değeri 490,00 €, birim maliyet 9,80 €/kg.
3. Kuzu alışı satırı: 287,50 + kesim 40,00 + nakliye 23,50 = 351,00 € doğru gösterildi.
4. Dış üretim emri: 60 kg girilince "Ana depoda 50 kg var." uyarısı çıktı. 40 kg ile **URT-2026-046** açıldı. Plan ön izlemesi: hammadde 588,00 € (60 kg ile), hizmet 36 × 5,50 = 198,00 €.
5. Sevk: onay penceresi → "Sevk edildi"; ET-2026-002'nin 40 kg'ı dış üretici deposuna geçti.
6. Kabul: teslim 34 adet; tüketilen 38 + iade 1 girilince "sevk edilen 40 kg olmalı" uyarısı çıktı. Fatura 190,00 € (önerilen 34 × 5,50 = 187,00 €) açıklamasız engellendi. Düzeltilince **SUC-2026-046** açıldı:
   - Maliyet: 372,40 + 190,00 = **562,40 €**.
   - EKP: **16,541176 → 16,54 €**; kâr 8,36 €, marj %33,57.
   - Verim: %89,47; miktar farkı −2 adet.
7. Lot ET-2026-002 ayrıntısı:
   - Hareketler: alış, 2 transfer, iade transferi, üretimde tüketim; her birinde belge no (FAT/TRF/URT) ve kullanıcı.
   - Toplam 12 kg / 117,60 €; "kalanla tutarlı" işareti çıktı.
   - İleri bağ: SUC-2026-046.
8. Transfer: varsayılan Ana depo → Satış aracı 1; SUC-2026-046'dan 10 adet → TRF-2026-0005. Stok durumunda ana depoda 24, araçta 10 adet.
9. Ürün penceresi:
   - Düzenleme değerleri doğru geldi; yeni ürün penceresi temiz açıldı.
   - Var olan kod (ET) ile kayıtta sunucunun Türkçe hatası pencerede gösterildi.
10. Çıkış: belirteç tarayıcıdan silindi; eski belirteçle `/auth/me` → 401.
11. Telefon genişliği:
   - Sayfa yatay taşmıyor (scrollWidth = 375).
   - Menü üst çubuktaki düğmeyle üstte açılıyor ve sayfa seçilince kapanıyor.

Yolda bulunan ve düzeltilen hatalar:

1. **Kök adres 404 veriyordu.** Yol eşleştirici sondaki "/" işaretini atarken kök yolu da boşaltıyordu. Düzeltildi ve `router.test.ts` eklendi.
2. **Kabulde lot numarası sunucuya gitmiyordu.** Lot numarası formda görünür bir alan olmadığından form değerlerine girmiyordu. Sunucu isteği "İstekte geçersiz alanlar var. (inputs.0.lot_no)" ile reddetti, yarım kayıt oluşmadı. Lot numarası artık emrin girdi listesinden alınıyor.
3. **Pencere formlarında başlangıç değerleri gelmiyordu (yalnız geliştirme modunda).** React StrictMode formu kurup söküp yeniden kuruyor; bu sırada `clearOnDestroy` başlangıç değerlerini siliyordu. Form artık her açılışta kendi temiz deposuyla kuruluyor. Önceki düzenlemenin değerlerinin yeni kayıt penceresinde kalmadığı ayrıca denendi.

Ayrıca düzeltilenler:

- Sunucu zamanları saat dilimi eki olmadan dönüyordu (api.md ISO 8601 + dilim istiyor); ekranlar 3 saat kayık gösterirdi. Artık `Z` ekli UTC dönüyor.
- Web'den açılan yeni dış üreticinin deposu yoktu; o cariyle emir açılamazdı. Artık otomatik açılıyor.
- Dar ekranda menü düğmesi başlığın üstüne biniyordu; düğme üst çubuğa taşındı.
- Tamamlanan emirde son adım "sürüyor" görünüyordu; düzeltildi.

Bilinen eksikler:

- Bileşen ve uçtan uca arayüz testleri otomatik değil (T-23).
- Üretim emrinde Model A tahmini yok (T-21).

## 24 Ekim 2026 — T-11 Görev 2 parçalama API'si

| Kontrol | Komut | Sonuç |
|---|---|---|
| Sunucu testleri | `docker compose run --rm --no-deps api pytest -q` | **126 geçti** (13 yeni: parçalama 12, Türkçe sayı biçimi 1) |
| Python kod denetimi | `… ruff check . && ruff format --check .` | Sorun yok |
| Web tipleri | `npm run api:types` + `tsc --noEmit` | Yeni uçlarla üretildi, hata yok |
| Canlı senaryo | Çalışan sistemde gerçek HTTP (deneme betiği, depoda değil) | Aşağıda |
| Bütünlük | `check_invariants` | 8/8 tutarlı (I-5 parçalama dahil) |

Canlı senaryo (KUZU-2026-012, 25 kg, 351,00 € = alış 287,50 + kesim 40,00 + nakliye 23,50):

1. Taslak: **PRC-2026-012**; beklenen maliyet 351,00 €; reçetenin 6 satırı açıldı.
2. Parçalar 22 kg girildi, fire boş bırakıldı: onay **422** "Bütün satırların fiili ağırlığı girilmeli (fire yoksa 0 yazın)."
3. Fire 0: onay **409 WEIGHT_IMBALANCE** "giriş 25 kg, çıkışlar 22 kg, fark 3 kg (tolerans 0,2 kg)". Bu ret deftere iz bırakmadı.
4. Fire 3 kg, miktar ağırlıklı ön izleme (kaydetmeden): 111,68 / 63,82 / 79,77 / 47,87 / 47,86 / fire 0,00.
5. Onay (değer ağırlıklı): toplam ve dağıtılan **351,00 €**. Paylar: but 123,41 (17,63 €/kg), sırt 83,34, omuz 72,12, kaburga 33,66, kıyma 38,47, fire 0,00.
6. Açılan lotlar: BUT-/SIRT-/OMUZ-/KABURGA-/KIYMA-PRC-2026-012. Kuzu lotu 0 kg / 0,00 €, beş çocuk lotu var.
7. BUT-PRC-2026-012: 7 kg, 123,41 €, SKT 29.10.2026. Bugün + 7 gün 31.10 olurdu; girdi lotunun SKT'sini geçemediği için 29.10. Kaynak: KUZU-2026-012.

Yolda bulunan ve düzeltilenler:

1. **Sunucu mesajlarında sayılar İngilizce biçimdeydi.** Örneğin "fark 3.000 kg" Türkçede üç bin diye okunur. Dış üretim ve alış mesajlarında da vardı ("40.000", "190.00 €"). Artık bütün kullanıcı mesajlarında ve bütünlük raporunda Türkçe biçim kullanılıyor: 3 kg, 0,2 kg, 1.543,50 €.
2. Fire satırı için birim maliyet "0 €/kg" yazılıyordu. Maliyet almayan satırlarda artık boş.

## 24 Ekim 2026 — T-12 Görev 2 parçalama web ekranları

| Kontrol | Komut | Sonuç |
|---|---|---|
| Web tip denetimi | `npx tsc -p tsconfig.app.json --noEmit` | Hata yok |
| Web kod denetimi | `npx oxlint` | Uyarı yok |
| Web birim testleri | `npm test` | 16 geçti (değişmedi) |
| Web derleme | `docker compose up -d --build web` | Başarılı; derin bağlantı (`/parcalama/2`) 8080'de açıldı, konsol hatasız |
| Bütünlük | `check_invariants` | Arayüz senaryosundan sonra 8/8 |

Tarayıcıda elle denenen senaryo (deneme için API'den yeni bir kuzu alışı yapıldı: KUZU-2026-013, 24 kg × 11,50 + kesim 40 + nakliye 20 = 336,00 €):

1. Yeni parçalama:
   - Reçete seçilince ana depodaki kuzu lotları listelendi (KUZU-2026-013 · 24 kg · 14,00 €/kg).
   - Lot seçilince ağırlık 24 kg olarak geldi; yöntem reçetenin varsayılanı (değer ağırlıklı).
   - "Taslağı aç" → **PRC-2026-013**.
2. Taslak: giriş maliyeti kalemleri gösterildi (276,00 + kesim 40,00 + nakliye 20,00 = 336,00 €); "6 kalemin ağırlığı girilmedi" bilgisi çıktı.
3. Beş parça girildi (6,5 / 4 / 5 / 3 / 3 kg), fire boş bırakıldı: "1 kalemin ağırlığı girilmedi; çıkışlar 21,5 kg, fark 2,5 kg". "Beklenen" sütunu standart oranla hesaplandı (but 24 × %27 = 6,48 kg).
4. Fire 0 → kırmızı "Ağırlık dengesi tutmuyor; onaylanamaz. … fark 2,5 kg (tolerans 0,2 kg)".
5. Fire 2,5 → yeşil "Ağırlık dengesi tutuyor". Değer ağırlıklı paylar 112,52 / 81,84 / 70,82 / 33,05 / 37,77 / 0,00, toplam 336,00 €. Elle kontrol: but payı 336 × (6,5 × 22) / 427 = 112,52 €.
6. Miktar ağırlıklıya geçince paylar ≈ 15,63 €/kg'a döndü. Kaburga ile kıyma arasındaki kuruş eşitliğinde reçete sırası öne geçti (46,89 / 46,88). Değer katsayısı sütunu bu yöntemde gizlendi.
7. Değer ağırlıklıya dönüp onaylandı:
   - Sonuç: toplam ve dağıtılan 336,00 €, fire 2,5 kg.
   - Parça lotları BUT-/SIRT-/OMUZ-/KABURGA-/KIYMA-PRC-2026-013 bağlantılı.
8. Lot BUT-PRC-2026-013:
   - Köken parçalama; 6,5 kg / 112,52 € (17,310769 €/kg).
   - SKT 29.10.2026, girdi lotununkiyle aynı.
   - Kaynak KUZU-2026-013 ("Parçalama" bağlantısı parçalama sayfasına gidiyor); hareket belgesi PRC-2026-013.
9. Reçeteler: yeni reçete penceresinde oran toplamı canlı gösterildi (%90 → kırmızı ve "Standart oranların toplamı %100 olmalı."). %100 yapılınca kaydedildi (KUZU-YARIM; API'de oranlar 0,6000 / 0,4000, fire maliyet taşımıyor).

Yolda bulunan ve düzeltilenler:

1. Dar ekranda (992 px altı) sayfa açılırken menü bir an açık başlayıp kapanıyordu; bu sırada yapılan tıklama menüye gidiyordu. Menünün başlangıç durumu artık ekran genişliğinden hesaplanıyor.
2. Lot sayfasında "Parçalama" süreci ve PRC belgeleri bağlantısızdı; parçalama sayfasına bağlandı.

Not: Deneme sırasında açılan KUZU-YARIM reçetesinin giriş ürünü yanlışlıkla "Doğal bağırsak" seçildi (deneme hatası). Geliştirme veritabanında duruyor; temiz örnek kayıtlar için `docker compose down -v` + `up`.

## 24 Ekim 2026 — T-14 Android satış ve T-15 gönderim

| Kontrol | Komut | Sonuç |
|---|---|---|
| Sunucu testleri | `docker compose run --rm --no-deps api pytest -q` | **134 geçti** (8 yeni: gönderim — AT-11 çift gönderim, AT-12 çevrimdışı bloke lot, kısmi ret, geçersiz satışlar, depo/rol, çekmeyle tutarlılık, yönetici listesi) |
| Python kod denetimi | `… ruff check . && ruff format --check .` | Sorun yok |
| Android birim testleri | `./gradlew testDebugUnitTest` | **17 geçti** (yeni: SaleRulesTest 4, PushMappingTest 2, giriş ayrıştırma 2) |
| Android derleme | `./gradlew assembleDebug` | Başarılı; Room sürüm 3, WorkManager 2.12.0 |
| Room göçü | Room'un ürettiği `createAllTables` ile göç SQL'i karşılaştırıldı | Birebir aynı; emülatörde sürüm 2 veritabanının üzerine kurulumda veri korundu |
| Bütünlük | `check_invariants` | Emülatör senaryosundan sonra 8/8 |

Emülatörde (Android 17) denenen senaryo; araçta SUC-2026-045 85 adet ve SUC-2026-046 10 adet vardı:

1. **Sürüm yükseltme:** Yeni APK eski kurulumun üzerine kuruldu. Göç 2 → 3 hatasız çalıştı, eşitleme yapıldı.
2. **Bağlantılı satış:**
   - Yeni satış, Market A, SUC-2026-045 ("Önerilen: ilk biten"); fiyat liste fiyatıyla geldi (24,90 €).
   - 90 adet girilince "Araçta kullanılabilir miktar: 85 adet." uyarısı çıktı; 30 adet → 747,00 €.
   - Kaydedilince "1 satış gönderilmeyi bekliyor", kullanılabilir 55 adet (araçta 85).
3. **Eski oturum:** Arka plandaki gönderim, eski sürümden kalan oturumda depo kimliği olmadığı için satışı göndermedi ve oturumu kapattı; satış telefonda kaldı. Yeniden girişten sonra "1 satış gönderildi · 2 kayıt güncellendi" → SAT-2026-0101. Düzeltme: böyle bir oturum artık uygulama açılışında tanınıyor ve doğrudan giriş isteniyor.
4. **Çevrimdışı satış:** Uçak modu açıldı. Market B'ye SUC-2026-045'ten 25 adet satıldı: "gönderilmeyi bekliyor", kullanılabilir 30.
5. **Çevrimdışıyken geri çağırma:**
   - Telefon çevrimdışıyken SUC-2026-046 sunucuda bloke edildi (geri çağırma ekranı T-16'da gelecek; şimdilik doğrudan veritabanından).
   - Telefon bunu bilmediği için Market C'ye 5 adet satıldı. "2 satış gönderilmeyi bekliyor".
6. **Bağlantı geldi:** Uçak modu kapatıldı. WorkManager iki satışı kendiliğinden gönderdi, sonra çekti.
   - SAT-2026-0102 (Market B) gönderildi.
   - SAT-2026-0103 (Market C) gönderildi; uyarı: "Geri çağrılmış lot satıldı (SUC-2026-046); satış kaydedildi, ihlal yöneticiye bildirildi."
   - Araçta SUC-2026-046 "BLOKE — satılamaz"; satış ekranında bu lot seçilemiyor.
7. **Sunucuda:**
   - Satışlar SAT-2026-0101/0102/0103. Maliyetler 544,76 / 453,97 / 82,71 €; ilk ikisi tasarım doğrulamasındaki rakamlarla aynı.
   - Araçta SUC-2026-045 30 adet, SUC-2026-046 5 adet.
   - Uyarı: "SAT-2026-0103: bloke SUC-2026-046 lotundan 5 adet Market C müşterisine satıldı (çevrimdışı satış). Müşteriyi geri çağırma listesine ekleyin."

Yolda bulunan ve düzeltilenler:

1. İkinci satışta aynı satış ekranı modeli yeniden kullanılırdı. Önceki satışın "kaydedildi" durumu yüzünden ekran hemen kapanırdı. Yazarken fark edildi; her satış ayrı anahtar alıyor.
2. Eski oturumda gönderim sessizce oturumu kapatıyordu; kullanıcı ancak eşitlemeye basınca fark ediyordu. Artık açılışta giriş isteniyor.
3. İhlal uyarısında miktar "5 birim" yazıyordu; artık ürün birimiyle ("5 adet", "4 kg").

Notlar:

- Bu senaryo geliştirme veritabanında iz bıraktı: SUC-2026-046 bloke, 3 satış. Temiz örnek kayıtlar için `docker compose down -v` + `up`.
- Android arayüz akışları elle (adb) denendi; otomatik arayüz testi yok.

## 27 Ekim 2026 — ekip paketi ve temiz kopyada kurulum denemesi

Ekip arkadaşına verilecek git paketi (`.bundle`) temiz bir klasöre açıldı ve README adımlarıyla sıfırdan kuruldu. Çalışan diğer sistemlere dokunmamak için ayrı Compose proje adı ve 18000/18080 portları kullanıldı.

| Kontrol | Sonuç |
|---|---|
| Paketten açma (`git clone AVATAR_Synera.bundle`) | Tamam; son commit ve `main` dalı geldi; `_kaynak/` ve `local.properties` depoda yok |
| `docker compose up --build -d` (`API_PORT=18000`, `WEB_PORT=18080`) | 59 saniyede hazır (temel imajlar önbellekteydi); sağlık denetimi `ok`, örnek kayıtlar yüklü (4 lot) |
| Web | Ana sayfa ve derin bağlantı (`/uretim`) HTTP 200 |
| Sunucu testleri | **134 geçti** |
| Web testleri (`npm ci` ile paketler sıfırdan) | **16 geçti** |
| Android (`local.properties` yok, `ANDROID_HOME` ile) | Derleme başarılı, **17 test geçti**, APK üretildi |
| `scripts/api_tipleri_yenile.sh` | Çalıştı (31 uç yolu) |

Yolda bulunan ve düzeltilen hatalar:

1. **Depodaki `docs/openapi.json` dosyasında Türkçe karakterler bozuktu** ("AVATAR â€” Synera", "Ãœretim"). Dosya daha önce Windows'ta Python'un standart girdisinden okunarak üretilmiş; metin yanlış kodlamayla çözülmüş. Bu dosyadan üretilen `web/src/api/schema.d.ts` yorumları da bozuktu. API açıklamasını (CR-008) etkiliyordu. Dosyalar doğru UTF-8 ile yeniden üretildi. Belgelerde, web ve sunucu kodunda başka bozuk karakter olmadığı tarandı.
2. **Yenileme betiği ilk hâlinde Windows'ta çalışmadı:** `python3` adı Microsoft Store'un yönlendirme kısayoluna çıkıyordu. Betik Node.js ile yeniden yazıldı (web tipleri için zaten gerekli, fazladan araç istemiyor).
3. Bu bilgisayarda 8000 portu başka bir projede kullanılıyor. Port `.env` ile değiştirilebiliyor (`API_PORT`, `WEB_PORT`); web geliştirme sunucusu da artık `API_PORT`'u okuyor.

Not: Bu deneme T-26'nın yerini tutmaz. Gerçek temiz kurulum testi, ekip arkadaşının kendi bilgisayarında yapılacak (`is_bolumu.md`).

## 27 Ekim 2026 — Görev 3, raporlar, yapay zekâ, 3D arayüz

### Otomatik testler

| Bölüm | Komut | Sonuç |
|---|---|---|
| Sunucu | `docker compose run --rm --no-deps api pytest -q` (+ `ruff check`, `ruff format --check`) | **166 geçti** (önceki 134 + 16 Görev 3 + 10 rapor + 6 yapay zekâ) |
| Yapay zekâ paketi | `docker compose run --rm --no-deps api sh -c "cd /ml && pytest -q"` | **4 geçti** |
| Web | `tsc -b`, `oxlint`, `vitest run`, `npm run build` | Tip ve lint temiz; **16 geçti**; üretim derlemesi başarılı |
| Android | `./gradlew assembleDebug testDebugUnitTest` | Derleme başarılı, **17 geçti**, APK üretildi |

Yeni sunucu testlerinin karşıladığı kabul testleri:

| Kabul testi | Test |
|---|---|
| AT-06 ileri izleme: ET-2026-001 → SUC-2026-045 → Market A 30 / B 25 / C 30, stok 0 | `test_at06_forward_trace_finds_markets` |
| AT-07 geri izleme: üç hammadde lotu, tedarikçiler, URT-2026-045 | `test_at07_backward_trace_finds_raw_materials_and_suppliers` |
| AT-08 geri çağırma: kaynak + türevler bloke, liste, CSV | `test_at08_recall_blocks_source_and_descendants_and_lists_markets`, `test_at08_contact_list_downloads_as_csv` |
| AT-09 ikinci kademe: kayıtlı ↔ bilinmiyor ayrımı | `test_at09_onward_delivery_is_certain_only_when_recorded` |
| AT-10 iade, imha, bütünlük | `test_at10_blocked_lot_is_returned_destroyed_and_books_stay_consistent` |
| AT-12 geri çağırmadan sonra çevrimdışı satış listede ve uyarıda | `test_at12_offline_sale_after_recall_is_flagged_in_the_list` |
| FR-309 demo senaryosu tutarlı (bütünlük 8/8) | `test_demo_scenario_is_consistent` |
| FR-601…607 raporlar demo verisiyle dolu, toplamlar doğru, CSV | `tests/test_reports.py` |
| FR-501…504 tahmin kaydı, sapma, model yokken iş akışı | `tests/test_ai.py` |

### Yapay zekâ ölçümleri (ayrılmış test verisi, `ml/models/metadata.json`)

| | Referans | Model |
|---|---|---|
| Model A paket MAE | 1,81 | 1,23 |
| Model A EKP MAE | 0,203 € | 0,127 € |
| Model B parça MAE | 0,212 kg | 0,135 kg |

Model B'de omuz payında model referanstan biraz kötü (0,150 → 0,158 kg); raporda yazılı. Ayrıntı: `reports/ai_degerlendirme.md`.

### Temiz kopyada demo profili

Ayrı Compose projesi (`-p avatar-temiz`), API 18100. Geliştirme veritabanına dokunulmadı.

| Kontrol | Sonuç |
|---|---|
| Sıfırdan kurulum, varsayılan `SEED_PROFILE=demo` | Günlükte "Demo senaryosu yüklendi: URT-2026-045 → SUC-2026-045, PRC-2026-012" |
| `GET /trace/forward/ET-2026-001` | ET-2026-001 → SUC-2026-045; Market A 30 (bilinmiyor), B 25 (kayıtlı), C 30 (bilinmiyor); stok boş |
| Sistemdeki gerçek tahmin (URT-2026-045) | Model A 84 paket, gerçek 85 (sapma +1); referans 82 (sapma +3). EKP tahmini 18,31 €, gerçek 18,16 € |
| Parçalama PRC-2026-012 | Dağıtılan 351,00 € = toplam; Model B tahmini her parçada gerçeğe 0,32 kg'dan yakın |

### Tarayıcıda deneme (web, API 18100)

- Ana sayfa: 3D gösterge kutuları (son EKP 18,16 €, açık geri çağırma, uyarı, bütünlük 8/8).
- Ana sayfadan "ET-2026-001 nereye gitti?": 3D lot zinciri, alıcılar, iletişim. "Geri çağırma başlat" → GC-2026-001; lotlar kırmızı (bloke), liste 3 market / 85 adet.
- Üretim raporu: EKP 18,16 €, YZ 84 / 18,31 €, sapmalar; üretim emri ekranında Model A kartı.
- Yapay zekâ ekranı: referans–model çubukları, örnek tahminler, gerçek kayıtlar, sınırlılıklar.
- Telefon genişliği (375 px): ana sayfa, izleme, geri çağırma, raporlar, rapor, yapay zekâ, satışlar, uyarılar — hiçbirinde yatay taşma yok. Önce izleme ekranı taşıyordu (516 px: uzun yön etiketleri ve üst çubuk başlığı); kısaltılarak düzeltildi.
- Düzeltilen: logodaki harf üst çubuğun satır yüksekliği yüzünden kutudan taşıyordu; antd `List` (kullanımdan kalkıyor) ve `rowKey` sıra numarası uyarıları giderildi.

### Emülatörde deneme (Android, Medium_Phone)

- Yeni görünüm: üst bant, gösterge kutuları (araçta lot, bloke lot, bekleyen satış), derinlikli kartlar.
- Uygulama, 24 Ekim'den kalan oturumla 8000 portundaki **başka bir projeye** bağlanmaya çalışıyordu (HTTP 400). Çıkış yapılıp sunucu adresi `http://10.0.2.2:18100` girildi; veri kümesi değiştiği için yerel kopya baştan çekildi (19 kayıt).
- Web/API'den KUZU-2026-012 geri çağrıldı (GC-2026-002, 6 lot) → telefonda "Verileri güncelle" → but ve sırt lotları kırmızı "BLOKE — satılamaz", "Bloke lot 2".
- Bulunan ve düzeltilen: sunucu sıfırlanınca telefon eski sunucuya gönderilmiş satışları "Son satışlar"da göstermeye devam ediyordu. Artık veri kümesi değişince gönderilmiş/reddedilmiş satış geçmişi siliniyor, bekleyen satışlar korunuyor. Room sorguları derlemede denetlendi; bu durum emülatörde ayrıca yeniden oluşturulmadı.

## 27 Ekim 2026 (akşam) — yeniden işleme, kabul testleri, paketten temiz kurulum

| Kontrol | Sonuç |
|---|---|
| Sunucu testleri (yeniden işleme dahil) | **170 geçti** |
| Kabul testleri `sh scripts/kabul_testleri.sh` (ayrı kopya, sıfırdan) | **23 geçti**; ET-2026-001 izlemesi 0,043 sn (`reports/kabul_testleri.md`) |
| Yeniden işleme tarayıcıda | İade gelen 12 paket SUC-2026-045 → YIS-2026-001, yeni lot SUC-YIS-2026-001; değer 217,90 + 3,60 = 221,50 € |

**Paketten temiz kurulum (T-26'nın bu bilgisayardaki provası).** Depo git paketinden ASCII yollu boş bir klasöre klonlandı. Yalnız README adımları izlendi: `.env.example` → `.env`, portlar 18300/18380.

| Adım | Sonuç |
|---|---|
| `docker compose up --build -d` | 99 saniyede hazır; sağlık `ok`; demo senaryosu yüklü |
| Web | Ana sayfa ve derin bağlantı (`/izleme/ET-2026-001`) HTTP 200 |
| Sunucu ve yapay zekâ testleri | 170 + 4 geçti |
| Kabul testleri (klondaki betikle) | 23 geçti |
| Web (`npm ci`, `tsc`, `vitest`) | 16 geçti |
| Android (`local.properties` yok, `ANDROID_HOME` ile) | Derleme başarılı, 17 test geçti, APK üretildi |

Not: Bu prova T-26'nın yerini tutmaz. Asıl temiz kurulum testi ekip arkadaşının bilgisayarında yapılacak.

## 28 Ekim 2026 — denetim düzeltmeleri, gerçek kullanım özellikleri, yeni arayüz, dil seçeneği

### Otomatik testler

| Bölüm | Komut | Sonuç |
|---|---|---|
| Sunucu | `docker compose run --rm --no-deps api pytest -q` | **215 geçti** (yeni 45: kullanıcı/rol 21, günlük işler 12, denetim düzeltmeleri 11, fason emri iptali 1) |
| Biçim | `ruff check` + `ruff format --check` | Temiz |
| Yapay zekâ | `cd /ml && pytest -q` | 4 geçti |
| Kabul (sıfırdan kurulum) | `sh scripts/kabul_testleri.sh` | **23/23**; ET-2026-001 ileri izleme 0,041 sn |
| Web | `npm test`, `tsc -b`, `oxlint` | **26 geçti** (FEFO 3, Code 128 3, çeviri eksiksizliği 4 dahil); derleme ve lint temiz |
| Android | `./gradlew testDebugUnitTest assembleDebug` | **22 geçti** (FEFO, son kullanma kuralı, çeviri dahil); APK üretildi |

Çalışırken bulunan iki test sorunu: gece yarısından sonra (yerel 00:0x) bir test UTC gününü bekliyordu, kod ise doğru olarak işletmenin yerel gününü kullanıyordu — test düzeltildi. "Perakende müşteri" eklenince iki liste testi güncellendi.

### Tarayıcıda deneme (sıfırdan kurulan kopya, nginx dahil)
- Güvenlik başlıkları (CSP, X-Frame-Options, nosniff) geliyor; uygulama CSP altında konsol hatası vermeden çalışıyor.
- `magaza1` ile giriş: menüde yalnız satış, stok okuma, izleme ve firma ekranları; üretim, geri çağırma yönetimi ve kullanıcılar görünmüyor.
- Yöneticinin açtığı hesapla ilk giriş "Yeni şifrenizi belirleyin" ekranına düşüyor; şifre değişince ana sayfa açılıyor.
- Mağaza satışı: ürün eklenince lot son kullanma tarihine göre seçildi (SIRT-PRC-2026-012), kartla 39,00 € kaydedildi; fiş/irsaliye ve barkodlu lot etiketi yazdırma sayfaları açıldı.
- Gün sonu, son kullanma takibi, sayım ve kullanıcılar ekranları; İngilizceye geçiş (sayı 1,543.50 biçimi); 278 px genişlikte yatay taşma yok.

### Emülatörde deneme (Android, Medium_Phone, API 18000)
- Giriş → yeni ana ekran (bugünkü satış, geri çağrılan lot uyarısı) → Stok (satışa kapalı lot etiketli).
- Satış: Market B → Narin Sucuk 3 adet (lot SUC-2026-045 kendiliğinden; geri çağrılan SUC-2026-046 listede yok) → Nakit → kaydet → sunucuya gönderildi (SAT-2026-0105).
- Gün sonu: 74,70 € nakit, araçta kalan mal; araç sayımı 26 adet → SAY-2026-0001, 1 lot eksik, stok 26'ya indi.
- Menüden English: ekran anında İngilizce, sayılar 74.70, tarih 23/12/2026; uygulama yeniden açılınca seçim korunuyor.


## 28 Ekim 2026 (ikinci tur) — alarm merkezi, denetim günlüğü, e-posta, panel grafikleri, hesaplayıcılar, turkuaz + 3B arayüz

### Otomatik testler

| Bölüm | Komut | Sonuç |
|---|---|---|
| Sunucu | `docker compose run --rm --no-deps api pytest -q` | **237 geçti** (yeni 22: art arda hatalı giriş alarmı ve e-postası, alarm görünürlüğü, denetim günlüğü ve CSV, bloke lot satış denemesi, geri çağırma alarmı, fiyat artışı kuralı ve eşik değişikliği, verim sapması, demo senaryosunun alarmsız olması, rapor e-postası ve giden kutusu, SMTP gönderimi (sahte sunucuyla: gönderildi / hata / bağlantı yok), fatura metni ayrıştırma, sayı biçimleri, EKP ve parçalama hesaplayıcıları, panel grafikleri) |
| Biçim | `ruff check` + `ruff format --check` | Temiz |
| Yapay zekâ | `cd /ml && pytest -q` | 4 geçti |
| Kabul (sıfırdan kurulum) | `sh scripts/kabul_testleri.sh` | **23/23**; ET-2026-001 ileri izleme 0,110 sn |
| Web | `npm test`, `tsc -b`, `oxlint` | **30 geçti** (yeni 4: günlük özet ve maliyet raporu metni, e-posta programı bağlantısı, geri çağırma bildiriminde her müşterinin yalnız kendi miktarını görmesi; çeviri eksiksizliği); derleme ve lint temiz |
| Android | `./gradlew testDebugUnitTest assembleDebug` | **22 geçti**; APK üretildi (üst çubuk turkuaz) |

Çalışırken bulunan sorunlar: geri çağırma artık ek alarmlar açtığı için bir eski test (yalnız ihlal uyarısını bekliyordu) güncellendi; çeviri testinin önbelleği yeni dosyaları görmüyordu (önbellek temizlenince doğru sonuç); uzun açıklamalar `t(` ile aynı satırda olmadığı için sözlük testinden kaçıyordu, tek satıra alındı ve çevrildi.

### Tarayıcıda deneme (sıfırdan kurulan kopya, nginx dahil)
- `kalite1` hesabına 3 yanlış şifre → yönetici girişinde zil 1, köşede "1 kritik alarm açık" bildirimi; denetim günlüğünde 3 "Hatalı giriş" (uyarı) ve 1 alarm (kritik).
- ET-2026-001 geri çağırması → kritik alarm; bloke SUC-2026-045'i mağazada satma denemesi → 409 `LOT_BLOCKED`, satış yazılmadı, kritik alarm açıldı. Üç alarm e-postası yönetici ve kaliteye "Kuyrukta" (SMTP tanımlı değil).
- Rapor gönder → Geri çağırma bildirimi → "Etkilenen müşterileri alıcı yap (3)": Market A 30, B 25, C 30 adet. Bulunan sorun: tek e-postada marketler birbirinin adresini ve miktarını görüyordu → düzeltildi, her müşteriye ayrı e-posta, yalnız kendi miktarı (test eklendi).
- Ne olur hesaplayıcısı: senaryo değerleriyle EKP 18,16 € (18,158824); VKP 24,90 € → brüt kâr 6,74 €, marj %27,07; faturadaki adet 86 yazınca uyarı. Parçalama: but 17,63 €/kg, sırt 20,84 €/kg, 351,00 € tam dağıtıldı; 3B sütunlar çizildi.
- Faturadan doldur: örnek metinden tedarikçi, belge no, tarih, iki satır (lot, miktar, fiyat, SKT) önerildi, forma aktarıldı, kaydedilmedi. Bulunan sorun: "Sucukluk et" adıyla eşleştiği hâlde "Kodla eşleşti" yazıyordu → ad önce denenir.
- Fiyat artışı alarmında fiyat "10,9 €" yazıyordu → iki basamak ("10,90 €").
- Telefon genişliğinde (375 px) ana sayfa ve panel tek sütun, yatay taşma yok.
- Ekran görüntüleri yeniden çekildi: 52 web (yeni 8) + 14 Android (emülatör Medium_Phone, turkuaz üst çubuk; satış SAT-2026-0107 Market B 1,5 kg sırt 39,00 € nakit, gönderildi) (`docs/ekran_goruntuleri`).

## 28 Ekim 2026 (üçüncü tur) — e-posta bildirimleri

### Otomatik testler

| Bölüm | Komut | Sonuç |
|---|---|---|
| Sunucu | `docker compose run --rm --no-deps api pytest -q` | **252 geçti** (yeni 15 `tests/test_email_notifications.py`: HTML + düz metin + ek, STARTTLS/giriş yalnız SMTP_USER doluysa, SMTP hatası günlüğe yazılıp döner, girişsiz 401 ve telefon rolü 403, izinsiz/pasif/geçersiz alıcı ve 21 alıcı 422, izinli alan adı 202, CSV eki ve not kaçışı, denetim kaydı, istek SMTP'yi beklemez, dakikada 5 sınırı (kullanıcı başına), giden kutusundan teslim, rol varsayılan abonelikleri, abonelik güncelleme ve yetkisiz tür 422, aboneye göre süzme, tekilleştirme, sayım farkı ve SKT uyarıları) |
| Biçim | `ruff check` + `ruff format --check` | Temiz |
| Web | `npm test`, `tsc -b`, `oxlint` | 30 geçti; derleme ve lint temiz |
| Kabul (sıfırdan kurulum) | `sh scripts/kabul_testleri.sh` | **23/23**; ET-2026-001 ileri izleme 0,020 sn (Mailpit bu kopyada çalışmıyor: e-postalar "Gönderilemedi" olur, iş akışı etkilenmez) |

Bulunan sorun: Test oturumunda Alembic'in `logging.fileConfig`'i önceden oluşmuş günlükçüleri kapatıyordu; "SMTP hatası günlüğe yazılır" testi tek başına geçip toplu çalıştırmada düşüyordu. Testte günlükçü açık tutuldu; üretimde göç ayrı süreçte çalıştığı için etkisi yok.

### Mailpit ile canlı deneme (demo yığını, API 18300, Mailpit 8025)
- Yönetici girişinde kural motoru SKT yaklaşan lot uyarısı açtı; e-posta 0,12 sn içinde Mailpit'teydi.
- `POST /reports/sales/email` → 202. E-posta `rapor_sales.csv` ekiyle (text/csv, 8 satır), notla ve HTML + düz metin olarak geldi.
- İzinsiz alıcı (`yabanci@kotu.example`) → 422, `details.rejected`. Aynı dakikada 6. gönderim → 429.
- Sayım farkı (ET-2026-002, −0,5 kg): uyarı e-postası 0,34 sn içinde abonelere ayrı ayrı gitti (yönetici, depo). Konu `[AVATAR UYARI] Sayım farkı`; gövdede sayım no, depo, eksik değeri ve `http://localhost:18380/sayim` bağlantısı vardı. Mailpit'te HTML görünümü düzgündü.
- Giden kutusunda bütün satırlar "Gönderildi".

## 29 Ekim 2026 — serbest e-postada açık röle kapatıldı

| Bölüm | Komut | Sonuç |
|---|---|---|
| Sunucu | `docker compose run --rm --no-deps api pytest -q` | **256 geçti** (yeni 4: `POST /mail` izinsiz/pasif adres 422, kayıtlı cari ve izinli alan adı kabul; rapor e-postası cariye gitmez; iki uç ortak dakika sınırı; toplu gönderim tek sayılır ve hep ya da hiç) |
| Biçim | `ruff check` + `ruff format --check` | Temiz |
| Web | `npm test`, `tsc -b`, `oxlint` | 30 geçti; derleme ve lint temiz |

Mailpit ile canlı deneme (demo yığını, API 18300):
- `magaza1` → `yabanci@kotu.example`: 422, `details.rejected`; → Market A (kayıtlı cari): 201, Mailpit'e düştü. Aynı dakikada 6. gönderim 429.
- `kalite1`, web'den **Rapor gönder → Geri çağırma bildirimi → Etkilenen müşterileri alıcı yap (3) → Gönder**: tek istek (`POST /mail/batch` 201), üç ayrı e-posta. Her markete yalnız kendi miktarı gitti (A 30, B 25, C 30 adet).
- Gün değişince yönetici girişinde kural motoru 4 lot için SKT uyarısı açtı; her uyarı 4 aboneye ayrı ayrı gitti (tekilleştirme alarm + alıcı başına).

## 31 Ekim 2026 — uçtan uca güvenlik denetimi

Ayrıntı ve kanıtlar: [docs/guvenlik/guvenlik_denetimi.md](../docs/guvenlik/guvenlik_denetimi.md).

| Bölüm | Komut | Sonuç |
|---|---|---|
| Sunucu | `docker compose run --rm --no-deps api pytest -q` | **274 geçti** (yeni: `tests/test_access_matrix.py` 9 test — 95 uç, 93 girişsiz → 401, 223 rol dışı → 403; `tests/test_security.py` 9 yeni test (3 eski şifre özeti testi yerinde) — CORS, `no-store`, hata ayrıntısı gizli, SQL enjeksiyonu, sunucu tarafı doğrulama, kaçışlı içerik, e-posta başlık enjeksiyonu, geçici kurulum şifreleri, `create_admin`) |
| Biçim | `ruff format --check` + `ruff check` | Temiz |
| Yapay zekâ | `… api sh -c "cd /ml && pytest -q"` | 4 geçti |
| Web | `npm test`, `npx tsc -b`, `npm run lint` | **32 geçti** (yeni `roles.test.ts`); tip ve lint temiz |
| Android | `./gradlew testDebugUnitTest assembleDebug` | **26 geçti** (yeni `TokenCipherTest` 4); APK derlendi |
| Kabul (sıfırdan kurulum) | `sh scripts/kabul_testleri.sh` | 23/23 |
| Canlı saldırı (demo yığını, nginx) | `sh scripts/guvenlik_denemesi.sh` | 27/27 reddedildi |
| Yedek | `sh scripts/yedek_denemesi.sh` | 38 tablo, 2 tetikleyici; döküm yedekle bire bir aynı |
| Bağımlılık | `npm audit --audit-level=moderate`; `pip-audit 2.10.1 -r requirements.txt` | 0 açık; 0 açık |
| Gizli bilgi | gitleaks v8.21.2 `git` (45 commit) ve `dir` | Bulgu yok |

Bulunan sorun: 4 test (`test_price_increase_rule_uses_editable_threshold` ve üç e-posta abonelik testi) alış tarihini "28 Ekim" diye sabit yazıyordu. Kurulum verisindeki son alış "dün" olduğu için 31 Ekim'de test alışı ondan önceye düştü ve fiyat artışı alarmı açılmadı. Testler bugünün tarihine bağlandı.

Emülatör (Medium_Phone, demo yığını):
- Eski APK'nın düz `token` değeri güncellemeden sonra silindi. Girişten sonra yalnız `token_sifreli` (`v1:…`) var. Uygulama kapatılıp açılınca oturum sürdü; çökme yok.
- Sunucu adresi web portu (`http://10.0.2.2:18380`) iken giriş ve eşitleme nginx üzerinden 200 döndü.

## 31 Ekim 2026 (ikinci tur) — Ayarlar (web ve telefon)

| Bölüm | Komut | Sonuç |
|---|---|---|
| Sunucu | `docker compose run --rm --no-deps api pytest -q` | **278 geçti**. Yeni `tests/test_settings.py` (4 test): oturum listesi bu oturumu işaretler ve belirteç döndürmez; diğer oturumları kapatma ve denetim kaydı; girişsiz 401; geçici şifreli satış elemanı önce 403 `PASSWORD_CHANGE_REQUIRED` alır, şifresini değiştirince eşitler. Yetki matrisi yeni iki ucu da kendiliğinden sınadı. |
| Biçim | `ruff format --check` + `ruff check` | Temiz |
| Web | `npm test`, `npx tsc -b`, `npm run lint` | 32 geçti; tip ve lint temiz |
| Android | `./gradlew testDebugUnitTest assembleDebug` | **29 geçti** (yeni `PasswordRulesTest` 3); APK derlendi |

**Tarayıcı (demo, `depo1`):**
- `/ayarlar` açıldı: hesap bilgileri, 3 açık oturum ("Bu oturum" işaretli), 9 bildirim türü, dil, sürüm ve durum doğru görünüyor.
- Yönetici bölümü `depo1`'de görünmüyor.

**Emülatör:**
- Ayarlar ekranı açıldı: hesap, eşitleme (sunucu, son eşitleme, bekleyen 0), dil, sürüm, cihaz kimliği.
- "Çıkış yap" onay istedi ve çıkış yapıldı.
- Geçici şifre senaryosu ayrı bir atılacak kopyada (`avatar-ayar`, API 18210) denendi:
  1. Yönetici, geçici şifreli `satis2`'yi açtı.
  2. Telefonda girişte zorunlu "Yeni şifrenizi belirleyin" ekranı açıldı.
  3. Kısa şifre telefonda reddedildi.
  4. Geçerli şifreyle `change-password` 200, ardından `sync/pull` 200 ("20 kayıt güncellendi").
  5. Kopya sonra silindi.
