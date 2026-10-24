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
