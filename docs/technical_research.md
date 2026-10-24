# Teknik Araştırma ve Teknoloji Seçimi

| | |
|---|---|
| Sürüm | v0.1 |
| Tarih | 24 Ekim 2026 |
| Durum | **Öneri — ekip onayı bekliyor.** Kararlar `docs/decisions/ADR-001…007` dosyalarında "Önerildi" durumunda. |
| Girdi | `requirements.md` v0.1, ekip cevapları: Go bilinmiyor, Kotlin ve Python kullanılabilir, gerçek veri yok |

**Kaynak ve doğrulama notu.** Sürüm numaraları 24 Ekim 2026'da resmî paket depolarından okundu (§1). Kütüphanelerin özellikleriyle ilgili bilgiler, resmî belgelerinde anlatılan yaygın ve köklü özelliklerdir. Ancak bu oturumda belge sayfaları tek tek açılıp doğrulanmadı. Bu yüzden her parça kurulumda (T-05) küçük bir "merhaba dünya" denemesiyle sınanacak; tutmayan bir bilgi çıkarsa bu belge düzeltilir.

---

## 0. Özet — önerilen yığın

| Bileşen | Öneri | Tek cümlelik gerekçe | Karar |
|---|---|---|---|
| Sunucu + REST API | **Python 3.12 + FastAPI + SQLAlchemy 2 + Alembic + PyMySQL** | Ekip Python biliyor; YZ de Python'da olacağı için sunucu ve YZ tek dilde, tek serviste birleşir; API belgesi otomatik üretilir. | ADR-001 |
| YZ çalışmaları | **scikit-learn**, sunucuyla aynı Python projesinde; tahminler sunucu API'sinden sunulur | Küçük tablo verisi için doğru araç; referans yöntem ve hata ölçümü hazır. | ADR-001, ADR-005 |
| Merkezi veritabanı | **MySQL 8.4** (Docker) | Şartname zorunluluğu; 8.4 serisi bakımı süren olgun seri. | ADR-007 |
| Web arayüzü | **React + Vite + TypeScript + Ant Design + TanStack Query** | Şartnamenin önerisi; tablo ve form ağırlıklı yönetim ekranlarına uygun bileşenler. | ADR-002 |
| Android | **Kotlin + Jetpack Compose + Room (SQLite) + WorkManager + Retrofit** | Google'ın güncel önerdiği yığın; Room, SQLite zorunluluğunu karşılar. | ADR-003 |
| Senkronizasyon | **Giden kuyruk + tekrar güvenlik anahtarı + sunucu değişiklik sırası + cihaz başına araç deposu** | Çevrimdışı satış, çift kayıt olmaması ve geri çağırmanın cihaza ulaşması birlikte sağlanır. | ADR-004 |
| Para ve miktar | Sunucuda `Decimal`, MySQL'de `DECIMAL`, Android'de tamsayı (kuruş/gram), JSON'da metin | Kayan noktalı sayı hiçbir katmanda kullanılmaz. | ADR-006 |
| Çalıştırma | **Docker Compose:** `mysql` + `api` + `web` | Değerlendirici tek komutla ayağa kaldırır. | ADR-007 |

Ortaya çıkan sistem: **üç çalışan servis** (veritabanı, API+YZ, web) ve **bir Android uygulaması**. Mimari ayrıntılar (veri modeli, API uçları, diyagramlar) Aşama 5'te `architecture.md`'ye yazılacak.

---

## 1. Sürüm bilgileri (24 Ekim 2026'da okundu)

| Paket | Son kararlı sürüm | Kaynak |
|---|---|---|
| fastapi | 0.162.0 | PyPI |
| sqlalchemy | 2.1.6 | PyPI |
| alembic | 1.20.1 | PyPI |
| pydantic | 2.14.1 | PyPI |
| pymysql | 1.2.3 | PyPI |
| uvicorn | 0.54.0 | PyPI |
| scikit-learn | 1.9.1 | PyPI |
| pytest | 9.1.1 | PyPI |
| react | 19.3.1 | npm |
| vite | 8.3.5 | npm |
| antd | 6.6.7 | npm |
| @mantine/core (karşılaştırma için) | 9.7.3 | npm |
| @tanstack/react-query | 5.104.5 | npm |
| openapi-typescript | 7.13.0 | npm |
| vitest | 5.0.5 | npm |
| Kotlin | 2.4.21 | Maven Central |
| Android Gradle Plugin | 9.4.1 | Google Maven |
| Compose BOM | 2026.09.00 | Google Maven |
| Room | 2.8.5 | Google Maven |
| WorkManager | 2.12.0 | Google Maven |
| Retrofit | 3.0.0 | Maven Central |
| kotlinx-serialization-json | 1.12.0 | Maven Central |
| Ktor server (karşılaştırma için) | 3.6.0 | Maven Central |
| MySQL (Docker resmî imajı) | 8.4 serisi: 8.4.13 (21.10.2026'da güncellendi); yeni seri: 26.10.0 (`latest`) | Docker Hub |

Sürümler kurulumda (T-05) sabitlenir. Android tarafında birbiriyle uyumlu sürümleri Android Studio'nun yeni proje şablonu belirler; listedekiler yalnızca üst sınırı gösterir. TypeScript sürümü de Vite şablonunun önerdiği sürüm olacak.

---

## 2. D-01 — Sunucu dili ve çatısı

**Bağlam.** Şartname "Go veya uygun modern teknoloji; REST API" diyor (TR-004). Ekip Go bilmiyor, Kotlin ve Python biliyor (CON-008). YZ tarafının pratikte Python olacağı açık (D-05).

### Seçenekler

| Ölçüt | A) Python + FastAPI | B) Kotlin + Ktor | C) Kotlin + Spring Boot |
|---|---|---|---|
| Ekip bilgisi | Var | Var (Android ile aynı dil) | Var (Spring ayrıca öğrenilmeli) |
| Öğrenme maliyeti (8 gün için) | Düşük | Orta (Ktor + veritabanı kütüphanesi) | Orta–yüksek (Spring kavramları) |
| YZ ile birleşme | Aynı süreçte, doğrudan çağrı | Ayrı Python servisi gerekir | Ayrı Python servisi gerekir |
| Çalışan servis sayısı (DB hariç) | 2 (API+YZ, web) | 3 (API, YZ, web) | 3 |
| Ondalık para | `decimal.Decimal` (standart kütüphane) | `BigDecimal` | `BigDecimal` |
| Veritabanı + şema göçü | SQLAlchemy 2 + Alembic (olgun) | Exposed veya JDBC + Flyway | JPA + Flyway |
| API belgesi (CR-008) | OpenAPI otomatik + hazır deneme arayüzü | Eklentiyle, daha çok elle iş | Ek kütüphaneyle otomatik |
| Tip güvenliği | Tip ipuçları + Pydantic doğrulaması (orta) | Güçlü | Güçlü |
| Android ile kod paylaşımı | Yok | Mümkün ama ek karmaşıklık getirir | Mümkün ama ek karmaşıklık getirir |
| Bu bilgisayardaki risk | Uygulama Denetimi bazı derlenmiş Python paketlerini engelleyebilir → Docker'da çalıştırılır | JDK kurulumu gerekir | JDK kurulumu gerekir |

### Önerilen seçenek (A) için sekiz soru

1. **Ne işe yarar?** FastAPI bir HTTP API çatısıdır: istek ve yanıtları Pydantic modelleriyle doğrular, OpenAPI belgesini koddan otomatik üretir. SQLAlchemy veritabanı erişimini, Alembic şema göçlerini yönetir. PyMySQL, saf Python ile yazılmış MySQL sürücüsüdür.
2. **Neden gerekli?** REST API zorunlu (TR-004). Maliyet, stok, lot ve geri çağırma kuralları tek bir yerde, sunucuda olmalı. Web ve Android aynı kuralları buradan kullanır.
3. **Alternatifleri?** Yukarıdaki B ve C. Go, ekip bilmediği için elendi.
4. **Artıları / eksileri?** Artıları: sunucu ve YZ tek dilde ve tek serviste; API belgesi bedavaya geliyor; `Decimal` standart; ekip zaten biliyor. Eksileri: (a) Python'da tip hataları çalışma anında ortaya çıkar — Pydantic şemaları, tip ipuçları ve testlerle azaltılır. (b) Android ile sunucu farklı dillerde, veri modelleri iki kez yazılır — senkron sözleşmesini küçük ve sabit tutarak yönetilir. (c) Uzun süren işlemci işi istekleri yavaşlatabilir — model eğitimi istek sırasında değil, çevrimdışı yapılır.
5. **Kısıtlara uygun mu?** Evet: "uygun modern teknoloji" şartını karşılar, REST, MySQL ile çalışır.
6. **Öğrenme ve geliştirme maliyeti?** Python bilen biri için FastAPI'nin temel kavramları (yol fonksiyonu, Pydantic modeli, bağımlılık) bir günden kısa sürede öğrenilir.
7. **Performans ve kaynak tüketimi?** Demo ölçeğinde (binlerce kayıt) fazlasıyla yeterli. Tek süreç, küçük bellek.
8. **Uzun vadede sürdürülebilir mi?** FastAPI, SQLAlchemy ve Alembic yaygın kullanılan ve 2026'da düzenli sürüm çıkaran projeler (§1).

**Öneri: A.** Belirleyici neden: YZ zaten Python olacağı için B ve C'de fazladan bir servis, fazladan bir derleme sistemi ve aralarında bir ağ bağlantısı ortaya çıkıyor; A bunların hiçbirini istemiyor. **Bu öneri, ekibin Python'a en az Kotlin kadar hâkim olduğu varsayımına dayanıyor.** Sunucuyu yazacak kişi Kotlin'de belirgin biçimde daha güçlüyse B (Ktor + ayrı Python YZ servisi) makul ikinci seçenek.

YZ kodu ayrı bir Python paketi (`ml/`) olarak durur. Sunucu bu paketi içe aktarır ve tahminleri kendi API'si üzerinden sunar (`/api/v1/ai/...`). Gerekirse ileride ayrı bir servise ayrılabilir; arayüz zaten ayrı.

---

## 3. D-02 — Web arayüzü

| Seçenek | Artı | Eksi | Karar |
|---|---|---|---|
| **React + Vite (tek sayfa uygulaması)** | Şartnamenin önerisi; en yaygın; Vite'ın hızlı geliştirme sunucusu | Ayrı derleme adımı | **Önerilen** |
| Next.js | Sunucu tarafı çizim, yönlendirme hazır | Bu projede sunucu tarafı çizime gerek yok; ek karmaşıklık | Hayır |
| Vue / Svelte | Sade | Şartname React öneriyor; ekip bilgisi bilinmiyor | Hayır |
| Sunucuda üretilen sayfalar (Jinja + htmx) | En az kod, tek dil | Değerlendirici büyük olasılıkla React bekliyor; zengin tablolar elle yazılır | Hayır |

**Bileşen kütüphanesi:** Ant Design (sıralama/süzme/özet satırlı tablolar, doğrulamalı formlar, tarih seçici; Türkçe dil paketi var) ile Mantine karşılaştırıldı. Ekranların çoğu tablo ve form (alış, emir, parçalama, raporlar) olduğu için **Ant Design** öneriliyor. Mantine daha hafif ama tablo özellikleri daha sınırlı.

**Yardımcılar:** TanStack Query (sunucudan veri çekme, önbellek, yükleniyor/hata durumları) ve openapi-typescript. openapi-typescript, FastAPI'nin ürettiği OpenAPI tanımından TypeScript tipleri üretir; böylece API sözleşmesi bozulursa web tarafı **derlenirken** hata verir.

**Sekiz soru (kısaca):** Yönetim ve rapor ekranları için gerekli (TR-005, FR-6xx). Öğrenme maliyeti ekibin React bilgisine bağlı (S-15). TypeScript bilinmiyorsa JavaScript ile de aynı yığın çalışır, yalnızca sözleşme denetimi kaybolur. Performans: tarayıcıda çalışır, demo ölçeğinde sorun yok. Hepsi yaygın ve bakımı süren projeler.

---

## 4. D-03 — Android yığını

| Konu | Öneri | Alternatif | Gerekçe |
|---|---|---|---|
| Arayüz | **Jetpack Compose** | XML görünümleri | Google'ın güncel önerdiği araç; daha az kod. Ekip XML'e daha hâkimse o da olur (S-15'e benzer soru). |
| Yerel veritabanı | **Room** | SQLDelight, doğrudan `SQLiteOpenHelper` | Resmî Jetpack kütüphanesi; verileri SQLite'ta saklar (TR-002); sorguları derleme anında denetler. |
| Ağ | **Retrofit + kotlinx.serialization** | Ktor istemcisi | En yaygın ve en çok örneği olan seçenek. |
| Arka planda senkron | **WorkManager** | Elle yazılmış servis | Ağ geldiğinde işi kendiliğinden yeniden dener; uygulama kapansa da çalışır. |
| Yapı | Tek aktivite, ViewModel + StateFlow, depo (repository) katmanı, **elle bağımlılık kurulumu** | Hilt ile bağımlılık enjeksiyonu | Küçük uygulamada Hilt'in kurulum maliyeti kazancından büyük. |

**Kritik ayrıntı — SQLite'ta para:** SQLite'ın ondalık (`DECIMAL`) tipi yoktur; `REAL` ikili kayan noktalı sayıdır. Bu yüzden Android'de tutarlar **tamsayı kuruş**, miktarlar **tamsayı gram/adet** olarak saklanır; ekranda `BigDecimal`'e çevrilir (ADR-006).

**Ortam:** Bu bilgisayarda Android Studio ve SDK kurulu değil (S-14). Android'i yapacak bilgisayar belirlenmeli.

---

## 5. D-04 — SQLite ↔ MySQL senkronizasyonu

Şartname bu yaklaşımın **açıklanmasını** istiyor (TR-007). İlgili gereksinimler: FR-403, FR-404, FR-405, NFR-003, NFR-004.

### Çözülecek sorunlar

1. Satış elemanı bağlantı yokken de satış yapabilmeli.
2. Bir satış sunucuya iki kez ulaşsa da tek kayıt oluşmalı (bağlantı yarıda kesilip yeniden denenince olur).
3. Geri çağırma başlayınca cihaz bunu mümkün olan en kısa sürede öğrenmeli.
4. İki cihaz aynı stoku satıp eksi stok oluşturmamalı.
5. Cihaz saatine güvenilmemeli.

### Seçenekler

| Seçenek | Açıklama | Değerlendirme |
|---|---|---|
| a) Hep çevrimiçi | Cihaz her işlemi doğrudan API'ye yapar; SQLite yalnız önbellek | En basit, ama bağlantı kesilince satış durur; şartnamenin "yerel saklama + senkronizasyon" beklentisini zayıf karşılar. |
| b) Tam anlık görüntü | Cihaz her seferinde bütün veriyi indirir, satışları gönderir | Basit, ama veri büyüdükçe ağırlaşır ve neyin değiştiğini (ör. geri çağırma) ayırt edemez. |
| **c) Giden kuyruk + değişiklik sırası** | Aşağıda | **Önerilen** — beş sorunun hepsini çözer, uygulaması orta zorlukta. |
| d) Hazır eşitleme altyapıları / çakışmasız veri tipleri | Genel amaçlı çift yönlü eşitleme | MySQL ↔ SQLite gibi farklı veritabanlarında ağır ve bu projenin ihtiyacının çok üstünde. |

### Önerilen yaklaşım (c)

- **Yukarı (cihaz → sunucu), giden kuyruk:** Satış cihazda tek bir SQLite işleminde yazılır: satış başlığı, satırlar, yerel stok düşümü ve "gönderilecekler" kuyruğuna bir kayıt. Her satışın cihazda üretilmiş benzersiz kimliği (UUID) vardır. WorkManager, ağ olduğunda kuyruğu `POST /api/v1/sync/push` ile gönderir.
- **Sunucuda tekrar güvenlik:** Satış kimliği veritabanında tekil (unique) tutulur. Aynı kimlik ikinci kez gelirse yeni kayıt açılmaz, ilk sonuç döndürülür (AT-11). Her satış sunucuda tek bir veritabanı işleminde yazılır: satış, satırlar, stok hareketleri (NFR-003).
- **Aşağı (sunucu → cihaz), değişiklik sırası:** Senkronize edilen her kayıt (ürün, müşteri, lot ve durumu, araç stoku, geri çağırma) değiştiğinde sunucuda artan bir **değişiklik numarası** alır. Cihaz son aldığı numarayı saklar ve `GET /api/v1/sync/pull?since=N` ile yalnızca yenileri çeker. Numara sunucuda üretildiği için cihaz saatine bağlı değildir.
- **Cihaz başına araç deposu:** Her satış cihazı kendi "araç deposundan" satar. Mal bu depoya sunucuda **depo transferi** ile yüklenir (FR-303; saha satışında sabah araca yükleme). O depodan yalnızca o cihaz satış yaptığı için iki cihaz aynı stoku satamaz. Cihaz, kendi deposunda olmayan miktarı satmayı reddeder (NFR-004).
- **Geri çağırma:** Lot durumu değişince değişiklik numarası artar. Cihaz çevrimiçiyken satış ekranını açmadan önce ve belirli aralıklarla çeker; bloke lotu satışta göstermez ve seçtirmez (FR-403).
- **Kalan uç durum (AT-12):** Cihaz çevrimdışıyken lot geri çağrıldı ve cihaz o lottan sattı. Önerilen kural: sunucu satışı **kaydeder** (mal fiziken müşteriye gitti; reddetmek izlenebilirlik kaydından gerçek bir teslimatı silmek olur), satışı "geri çağırma ihlali" olarak işaretler ve o müşteriyi geri çağırma iletişim listesine otomatik ekler. Gıda güvenliği açısından doğru olan, bu teslimatı görünür kılmaktır.

### Çakışma kuralları

| Veri | Yön | Kural |
|---|---|---|
| Ana veriler (ürün, müşteri, fiyat) | Sunucu → cihaz | Sunucu kazanır; cihaz değiştirmez. |
| Lot durumu (aktif/bloke) | Sunucu → cihaz | Sunucu kazanır. |
| Satışlar | Cihaz → sunucu | Yalnızca eklenir, güncellenmez; çakışma olamaz; tekrar gelirse yok sayılır. |
| Stok bakiyesi | Sunucu → cihaz | Sunucu hareketlerden yeniden hesaplar; cihazdaki bakiye her çekişte sunucununkiyle değiştirilir. |

**Maliyet:** Sunucuda iki uç nokta + değişiklik numarası; Android'de bir kuyruk tablosu + bir WorkManager işi. 2 kişi-günü civarında (T-15). Akış diyagramı mimaride çizilecek.

---

## 6. D-05 — Yapay zekâ yaklaşımı

### Kütüphane

| Seçenek | Değerlendirme |
|---|---|
| **scikit-learn** | Küçük tablo verisinde regresyon için standart araç. Doğrusal (Ridge) ve ağaç tabanlı (HistGradientBoosting; aralık tahmini için çeyreklik/quantile kaybı) modeller, zaman sıralı çapraz doğrulama, MAE/MAPE ölçüleri tek pakette. **Önerilen.** |
| statsmodels | Doğrusal modellerde güven aralığı güçlü; ağaç modelleri yok. Gerekirse yardımcı. |
| LightGBM / XGBoost | Ek bağımlılık; birkaç yüz satırlık veride scikit-learn'e anlamlı üstünlüğü beklenmez. |
| Derin öğrenme (PyTorch vb.) | Bu veri boyutu için aşırı; aşırı öğrenme riski yüksek. |
| Büyük dil modeli | Sayısal tahmin için uygun değil, ölçülebilirliği zayıf, dış API maliyeti getirir. (İsteğe bağlı fatura okuma için ayrıca düşünülebilir — FR-551.) |

### Model A — üretim verimi ve EKP (FR-501, FR-502)

- **Hedef:** verim = teslim alınan mamul kg / kullanılan et kg (AS-007).
- **Girdiler:** mamul/reçete, dış üretici, et tedarikçisi, et miktarı, ay (mevsim).
- **EKP tahmini:** Hammadde maliyeti emir açılırken kullanılan lotların fiyatlarından **kesin olarak bilinir**. Belirsiz olan çıkacak paket sayısıdır: tahmini paket = verim × et kg / paket ağırlığı. EKP tahmini = (hammadde maliyeti + hizmet birim ücreti × tahmini paket) / tahmini paket. Böylece model, gerçekten belirsiz olan kısmı tahmin eder; hesap şeffaf kalır.
- **Referans yöntem:** ürün bazında geçmiş ortalama verim.

### Model B — parçalama verimi (FR-503, FR-504)

- **Hedef:** her parçanın (ve firenin) giriş ağırlığı içindeki payı.
- **Girdiler:** hayvan türü (kuzu/koyun/keçi), giriş ağırlığı, tedarikçi, ay.
- **Kütle dengesi:** tahmin edilen paylar 1'e tamamlanacak biçimde ölçeklenir; tahmin de ağırlık dengesi kuralına (FR-205) uyar.
- **Referans yöntem:** reçetedeki standart oran × giriş ağırlığı (FR-201). İkinci referans: tür bazında geçmiş ortalama oran.

### Değerlendirme (FR-506, AT-13)

- **Zaman bazlı ayırma:** kayıtların kronolojik ilk %80'i eğitim, son %20'si test. Model seçimi eğitim kısmında zaman sıralı çapraz doğrulamayla yapılır; test kısmına yalnızca son ölçümde bakılır.
- **Ölçüler:** ortalama mutlak hata — MAE (kg, paket, €), yüzde hata — MAPE, iyileşme = (referans MAE − model MAE) / referans MAE. Model B'de parça bazında ayrı ayrı.
- **Sızıntı önlemi:** Tahmin, emir/parçalama **açılırken** üretilip kaydedilir. "Tahmin – gerçek – sapma" ekranı, sonradan yeniden hesaplanan değil, o anda kaydedilen tahmini gösterir.

### Veri (FR-505, FR-507)

Gerçek veri yok (AS-011). Sabit tohumlu bir sentetik veri üretici yazılır; etkiler açıkça parametre olarak tanımlanır: tedarikçi farkı, dış üretici farkı, mevsim (yazın daha fazla kuruma kaybı), ağırlık–parça oranı ilişkisi (ağır hayvanda fire ve yağ payı artar), rastgele gürültü. Örnek ölçek: 2 yıllık ≈ 300 üretim emri ve ≈ 600 parçalama.

**Dürüst sınırlılık:** Model yalnızca üreticiye yazdığımız ilişkileri öğrenebilir. Sentetik veride ölçülen başarı, gerçek işletmedeki başarının kanıtı değildir. Gerçek veri geldiğinde aynı akışla yeniden eğitilir ve ölçülür. Bu, raporda ayrı bölüm olarak yazılacak.

### Sunum

Eğitim, çevrimdışı bir betikle yapılır ve model dosyası kaydedilir. Sunucu başlarken modeli yükler. Tahminler `POST /api/v1/ai/production-forecast` ve `POST /api/v1/ai/cutting-forecast` uçlarından verilir. Değerlendirme raporu `reports/` altına yazılır. Bu bilgisayarda scikit-learn daha önce engellendiği için YZ kodu Docker'daki Linux konteynerinde çalıştırılır (R-08).

---

## 7. D-06 — Para ve miktar gösterimi

| Katman | Öneri |
|---|---|
| Sunucu (Python) | Her yerde `decimal.Decimal`; `float` yasak. Yuvarlama tek bir yardımcı fonksiyonda, ticari yuvarlama (yarım yukarı). |
| MySQL | Defter tutarları `DECIMAL(14,2)` (kuruş); birim maliyet `DECIMAL(14,6)` (yalnız bilgi ve gösterim); miktar `DECIMAL(12,3)` (kg için gram). |
| Lot değeri | Lot değeri kuruşların toplamıdır. Lottan çıkışta maliyet = kalan değer × çıkan miktar / kalan miktar (kuruşa yuvarlanır); **son çıkış kalan değerin tamamını alır**. Böylece lot değeri tam sıfıra iner, birikmiş yuvarlama farkı kalmaz (18,16 × 85 sorununun çözümü). |
| Maliyet dağıtımı | En büyük kalan yöntemi; eşitlikte reçete sırası (AT-03). |
| JSON | Ondalıklar **metin** olarak taşınır (`"18.1588"`). JavaScript ve Kotlin'in varsayılan sayı çözümlemesi kayan noktalıdır. |
| Android SQLite | Tamsayı: kuruş ve gram/adet; ekranda `BigDecimal`. |

Alternatif: sunucuda da her yerde tamsayı kuruş. Doğru bir yöntem, ama birim maliyet gibi 2'den fazla ondalık gereken yerlerde ölçek takibi karmaşıklaşıyor. `Decimal` daha okunaklı.

---

## 8. D-07 — Lot ağı sorgusu

| Seçenek | Değerlendirme |
|---|---|
| **Uygulama içinde katman katman gezinme** (ziyaret edilenler kümesiyle) | Okunaklı, döngüye karşı güvenli, ileri ve geri izlemede aynı kod; birim testi kolay. Demo ölçeğinde hızlı. **Önerilen.** |
| MySQL 8 özyinelemeli sorgu (`WITH RECURSIVE`) | Tek sorgu, hızlı; ama mantık SQL'e gömülür, test ve hata ayıklama zorlaşır. Performans gerekirse sonradan geçilebilir. |
| Graf veritabanı | Gereksiz ek sistem. |

Asıl önemli olan sorgu biçimi değil, lot bağlantı tablosunun eksiksiz dolmasıdır (FR-302). O kural mimaride tanımlanacak.

---

## 9. D-08 — Çalıştırma ve dağıtım

- **Docker Compose:** `mysql` (8.4), `api` (Python 3.12 tabanlı imaj; açılışta şema göçü + veritabanı boşsa örnek kayıt yükleme), `web` (React derlemesi + statik sunucu). Değerlendirici için tek komut: `docker compose up --build`.
- **MySQL sürümü:** 8.4 serisi hâlâ güncelleniyor (8.4.13, 21.10.2026). `latest` etiketi yeni 26.x serisini gösteriyor. Sürücü uyumluluğu ve kaynak bolluğu nedeniyle **8.4** öneriliyor. Docker Hub'daki `lts` etiketinin hangi seriyi gösterdiği bu araştırmada netleşmedi; sabit `8.4` etiketi kullanılacak.
- **Android:** İmzalı APK, GitHub "Release" ekine konur; derleme adımları README'de.
- **Windows:** Docker Desktop + WSL2 gerekir; bu bilgisayarda ikisi de kurulu ama kapalı.
- **Yedek:** Docker çalışmazsa elle kurulum adımları README'de ayrıca yazılır.

---

## 10. D-09 — Kimlik doğrulama (NFR-007)

En sade güvenli çözüm: rolleri olan (yönetici, satış) kullanıcı tablosu; parolalar standart kütüphanedeki `hashlib.scrypt` ile özetlenir (ek bağımlılık yok); girişte rastgele bir oturum belirteci üretilip sunucuda saklanır ve `Authorization: Bearer` başlığıyla gönderilir. JWT de olurdu ama iptal etmek zorlaşır; OAuth gibi dış kimlik sağlayıcılar bu prototip için aşırı. Demo kullanıcıları örnek kayıtlarla gelir; parolaları README'de "yalnız demo" diye belirtilir.

---

## 11. D-10 — API belgesi

FastAPI'nin ürettiği OpenAPI tanımı, `openapi.json` olarak depoya da konur; böylece değerlendirici sistemi çalıştırmadan görebilir. Çalışan sistemde hazır deneme arayüzü (`/docs`) bulunur. Buna ek olarak `docs/api.md`'de ana akışlar örnek isteklerle anlatılır (CR-008).

---

## 12. D-11 — Şema göçü, test ve kod kalitesi araçları

| Bileşen | Araçlar |
|---|---|
| Sunucu + YZ | Alembic (şema göçü), pytest (birim + API), Docker'daki MySQL'e karşı entegrasyon testleri, Ruff (biçim + denetim) |
| Kabul testleri | `tests/` altında pytest senaryoları; çalışan API'ye istek atar (AT-01…AT-12, AT-15) |
| Web | TypeScript derleyicisi (`strict`) + Vite şablonunun denetim aracı oxlint (create-vite 9.3.1 şablonu ESLint yerine oxlint getiriyor); saf fonksiyonlar için Vitest |
| Android | JUnit ile ViewModel ve senkron mantığı testleri (sahte API ile); Room için bellek içi veritabanı testi |

---

## 13. Bilinçli olarak eklemediklerimiz

Mesaj kuyrukları, mikroservisler, Kubernetes, GraphQL, ayrı kimlik sunucusu, Kotlin Multiplatform ile kod paylaşımı, büyük dil modeliyle tahmin. Gerekçe: 8 günlük süre, sadelik ilkesi ve hiçbirinin değerlendirme ölçütlerine doğrudan katkısı olmaması (R-13).

---

## 14. Kaynaklar

- Sürümler (24.10.2026): PyPI (pypi.org), npm (npmjs.com), Maven Central (repo1.maven.org), Google Maven (dl.google.com/dl/android/maven2), Docker Hub — MySQL resmî imajı (hub.docker.com/_/mysql).
- Resmî belgeler (kurulumda doğrulanacak): FastAPI (fastapi.tiangolo.com), SQLAlchemy (docs.sqlalchemy.org), Alembic (alembic.sqlalchemy.org), scikit-learn (scikit-learn.org), Android Developers — Room, WorkManager, Jetpack Compose ve çevrimdışı öncelikli uygulama rehberi (developer.android.com), MySQL 8.4 Başvuru Kılavuzu — `DECIMAL` ve `WITH RECURSIVE` (dev.mysql.com/doc), React (react.dev), Vite (vite.dev), Ant Design (ant.design).
