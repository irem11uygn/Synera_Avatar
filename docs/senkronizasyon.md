# SQLite ↔ MySQL Senkronizasyonu: Veriler Nasıl Tutarlı Kalır

| | |
|---|---|
| Şartname maddesi | Teknik gereksinimler: "SQLite ile MySQL arasındaki senkronizasyonun nasıl tutarlı tutulacağı açıklanmalıdır" |
| Gereksinimler | TR-001, TR-002, TR-007, FR-403…FR-405; karar: ADR-004 |
| Kod | Sunucu: `backend/app/services/sync.py` (çekme), `backend/app/services/sales.py` (gönderme) · Android: `data/repo/AvatarRepository.kt`, `sync/SyncWorker.kt`, `data/local/` (Room/SQLite) |

## 1. Tek cümleyle

**Gerçeğin tek kaynağı sunucudaki MySQL'dir.** Telefondaki SQLite yalnız iki şey tutar:
- Satış için gereken verinin bir kopyası (ürünler, müşteriler, araçtaki lotlar ve stok).
- Henüz gönderilmemiş satışlar.

Satış telefona hemen yazılır. Bağlantı gelince sunucuya gönderilir. Sunucu her satışı **bir kez** ve kendi kurallarıyla deftere işler.

```mermaid
sequenceDiagram
    participant A as Android (SQLite)
    participant S as Sunucu (FastAPI)
    participant M as MySQL
    Note over A: Satış → yerel SQLite (PENDING), client_uuid
    A->>S: POST /sync/push (bekleyen satışlar)
    S->>M: Her satış kendi alt işleminde: lot + stok + hareket
    S-->>A: Satış başına ACCEPTED / ACCEPTED_WITH_WARNING / DUPLICATE / REJECTED
    A->>S: GET /sync/pull?since=N
    S->>M: change_seq > N olan kayıtlar
    S-->>A: ürünler, müşteriler, araç lotları (durum dahil), stok, next_since, dataset_id
    Note over A: Yerel kopya güncellenir; bloke lotlar satışa kapanır
```

## 2. Sunucudan telefona: çekme (`GET /sync/pull`)

| Sorun | Çözüm |
|---|---|
| Her seferinde bütün veriyi indirmek yavaş | Eşitlenen her tabloda **değişiklik numarası** (`change_seq`) var. Bir satır eklenince ya da değişince tek satırlık bir sayaçtan yeni numara alır. Telefon son aldığı numarayı (`since`) gönderir; yalnız ondan sonra değişenler gelir. |
| Aynı anda yazılan bir kayıt atlanır mı? | Sayaç satır kilidiyle artırılır, numaralar işlenme sırasıyla dağılır. Sunucu yanıtı sayacın o anki değerine (`upto`) kadar keser; sonradan kaydedilenler bir sonraki çekmeye kalır. READ COMMITTED yalıtımında da kayıt atlanmaz. |
| Sunucu sıfırdan kuruldu ya da yedekten döndü | Yanıtta **veri kümesi kimliği** (`dataset_id`, her kurulumda yeni UUID) var. Değişmişse ya da `next_since` telefondakinden küçükse telefon yerel kopyasını siler ve baştan çeker. |
| Geri çağrılan lot telefonda satılmaya devam eder mi? | Lot bloke edilince değişiklik numarası artar. Bir sonraki çekmede telefon lotu `BLOKE` görür ve satış ekranında seçtirmez; kart kırmızıdır, "Geri çağrıldı: satılamaz" yazar. |
| Telefon hangi stoku görür? | Yalnız kullanıcının **kendi araç deposundaki** lotlar ve bakiyeler. Gösterilen satılabilir miktar = sunucudaki bakiye − henüz gönderilmemiş yerel satışlar. Böylece çevrimdışıyken aynı stok iki kez satılmaz. |

## 3. Telefondan sunucuya: gönderme (`POST /sync/push`)

| Sorun | Çözüm |
|---|---|
| Bağlantı yokken satış | Satış önce SQLite'a yazılır (`PENDING`). Bağlantı gelince WorkManager arka planda gönderir; kullanıcı "Verileri güncelle" ile de tetikleyebilir. Önce gönderilir, sonra çekilir. Aynı anda iki eşitleme çalışmasın diye kilit (Mutex) kullanılır. |
| Aynı satış iki kez gönderilirse (yanıt kayboldu, yeniden deneme) | Her satış telefonda üretilen **benzersiz kimlikle** (`client_uuid`) gelir. Veritabanında bu sütun benzersizdir. İkinci kez gelen satış yeni kayıt açmaz; ilk sonuç `DUPLICATE` olarak geri döner. |
| Bir satış hatalıysa diğerleri ne olur? | Her satış kendi **alt işleminde** (savepoint) yazılır. Reddedilen satış geri alınır, aynı gönderimdeki diğerleri kaydedilir. Reddedilenin Türkçe hata mesajı telefonda gösterilir. |
| Telefondaki saat yanlışsa | Cihaz zamanı yalnız bilgi olarak saklanır (`sold_at`). Belge numarası ve sıralama sunucu zamanıyla (`received_at`) yapılır. |
| Para ve miktar hassasiyeti | API'de ondalık **metin** olarak taşınır ("24.90"). Telefonda kuruş ve gram cinsinden **tam sayı** tutulur. Kayan noktalı sayı hiçbir yerde kullanılmaz (ADR-006). |

## 4. Özel durum: çevrimdışıyken geri çağrılmış lot satıldı

Telefon son eşitlemeden sonra bloke edilen bir lotu, haberi olmadan satabilir. Mal müşteriye gitmiştir. Bu yüzden sunucu satışı **reddetmez**, reddetseydi izi kaybolurdu (ADR-004). Bunun yerine:

1. Satış ve stok hareketi kaydedilir. Satış `recall_violation` olarak işaretlenir; telefona `ACCEPTED_WITH_WARNING` döner.
2. Yöneticiye **uyarı** düşer: web'de menüde sayı ve "Uyarılar" ekranı.
3. Müşteri, geri çağırma listesinde **"geri çağırmadan sonra satış"** işaretiyle görünür ve iletişim listesine (CSV) girer.

Bu senaryo otomatik testle denetlenir (`backend/tests/test_trace_recall.py::test_at12_offline_sale_after_recall_is_flagged_in_the_list`). Emülatörde uçak moduyla da denendi.

## 5. Tutarlılığın sınanması

| Sınama | Nerede |
|---|---|
| Artımlı çekme, değişen kayıtlar, veri kümesi kimliği | `backend/tests/test_sync_pull.py` |
| Tekrar güvenliği, satır = lot = hareket, alt işlem, çevrimdışı ihlal | `backend/tests/test_sync_push.py`, `test_trace_recall.py` |
| Telefondaki kurallar (satılabilir miktar, gönderim eşlemesi, birimler) | `android/app/src/test/` (SaleRulesTest, PushMappingTest, UnitsTest) |
| Defter ile özetlerin tutarlılığı (I-1…I-8) | Web → Raporlar → Bütünlük raporu; `backend/tests/test_integrity.py` |
