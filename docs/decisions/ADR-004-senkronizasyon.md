# ADR-004: SQLite ↔ MySQL senkronizasyonu — giden kuyruk, değişiklik sırası, araç deposu

- Durum: **Kabul edildi** (ekip onayı: 24.10.2026)
- Tarih: 24.10.2026
- İlgili gereksinimler: TR-007, FR-403, FR-404, FR-405, NFR-003, NFR-004, AT-11, AT-12
- Ayrıntı: `docs/technical_research.md` §5 (D-04)

## Bağlam
Android satış uygulaması bağlantı yokken de satış yapmalı; satışlar sunucuya bir kez ve eksiksiz ulaşmalı; geri çağırma cihaza hızla inmeli; iki cihaz aynı stoku satamamalı; cihaz saatine güvenilmemeli.

## Seçenekler
1. Hep çevrimiçi — bağlantı kesilince satış durur.
2. Her seferinde tam veri indirme — veri büyüdükçe ağırlaşır, değişiklikleri ayırt edemez.
3. **Giden kuyruk + tekrar güvenlik anahtarı + sunucu değişiklik sırası + cihaz başına araç deposu.**
4. Genel amaçlı çift yönlü eşitleme altyapıları — bu ihtiyaç için aşırı.

## Karar
Seçenek 3:
- Satış cihazda tek SQLite işleminde yazılır ve cihazda üretilen UUID ile kuyruğa girer. WorkManager kuyruğu `POST /api/v1/sync/push` ile gönderir.
- Sunucuda satış kimliği tekildir; tekrar gelen satış yeni kayıt açmaz, ilk sonuç döner. Her satış tek veritabanı işleminde yazılır.
- Senkronize edilen kayıtlar değiştikçe sunucuda artan bir değişiklik numarası alır. Cihaz `GET /api/v1/sync/pull?since=N` ile yalnız yenileri çeker.
- Her cihaz kendi araç deposundan satar; mal o depoya sunucuda depo transferiyle yüklenir.
- Çevrimdışıyken geri çağrılmış lot satılırsa: sunucu satışı kaydeder, "geri çağırma ihlali" olarak işaretler ve müşteriyi geri çağırma listesine ekler.

## Sonuçlar
- Çift kayıt ve eksi stok yapısal olarak önlenir; geri çağırma her çekişte cihaza iner.
- Sunucuda değişiklik numarası tutulması, Android'de kuyruk tablosu ve bir arka plan işi gerekir (≈ 2 kişi-günü).
- Araç deposu, saha satışını modeller. Satış dükkândan yapılacaksa, tek cihaz için aynı yapı "dükkân deposu" olarak çalışır.
- (T-09'da görüldü) Sunucu veritabanı sıfırlanınca cihaz eski numarasıyla çekmeye devam etti ve silinmiş bir lotu araç stokunda göstermeyi sürdürdü. Çekme yanıtına veri kümesi kimliği (`dataset_id`) eklendi; kimlik değişirse ya da sunucunun numarası cihazınkinden küçükse cihaz yerel kopyasını baştan kurar (`architecture.md` §5).
