# API Sözleşmesi

| | |
|---|---|
| Sürüm | v0.1 (taslak — kod yazılınca FastAPI'nin ürettiği `openapi.json` asıl kaynak olur; bu belge ana akışları anlatır) |
| Tarih | 24 Ekim 2026 |
| Karşıladığı teslimat | CR-008 "API açıklaması" |
| Dayanak | `architecture.md`, `data_model.md` |
| Uygulanan uçlar (27.10.2026) | Aşağıdaki tablolardaki bütün uçlar uygulandı. Yalnız `POST /sales` (web kanalından satış) yok: satışlar Android'den `/sync/push` ile gelir. Uç listesinin asıl kaynağı `docs/openapi.json` ve çalışan sistemde `/docs`. |
| Önceki not (24.10.2026) | `GET /health`; `POST /auth/login`, `GET /auth/me`, `POST /auth/logout`; `GET /stock`; `GET, POST /products`, `PUT /products/{id}`; `GET, POST /partners`, `PUT /partners/{id}`; `GET /warehouses`; `POST, GET /purchases`, `GET /purchases/{id}`; `GET /lots`, `GET /lots/{lot_no}`, `GET /lots/{lot_no}/movements`; `POST, GET /transfers`; `POST, GET /production-orders`, `GET /production-orders/{id}`, `POST …/{id}/ship`, `…/complete`, `…/cancel`; `GET, POST /cutting-recipes`, `GET /cutting-recipes/{id}`; `POST, GET /cuttings`, `GET, PUT /cuttings/{id}`, `POST /cuttings/{id}/preview`, `POST /cuttings/{id}/approve`; `GET /sync/pull`, `POST /sync/push`; `GET /sales`, `GET /sales/{id}`; §3'teki hata biçimi. Farklar: satış rolü ürünleri web uçlarından değil çekme senkronundan alır; üretim emrine Model A tahmini T-21'de eklenecek. Diğer uçlar sırayla eklenecek. |

## 1. Genel kurallar

| Konu | Kural |
|---|---|
| Taban yol | `/api/v1` |
| Biçim | JSON, UTF-8 |
| Kimlik | `Authorization: Bearer <belirteç>` (`/auth/login` ve `/health` hariç her uçta) |
| Ondalıklar | **Metin** olarak: `"18.158824"`, `"1543.50"` (ADR-006). Miktarlar ürünün temel biriminde (kg veya adet). |
| Tarih/saat | ISO 8601 (`2026-10-26`, `2026-10-26T09:30:00+03:00`). Sunucu zamanları UTC olarak `Z` ekiyle döner (`2026-10-24T11:51:59Z`); ekranlar yerel saate çevirir. |
| Listeler | `?limit=50&offset=0`; yanıt `{"items": [...], "total": n}` |
| CSV | Rapor ve geri çağırma uçlarında `?format=csv` veya `/export.csv` |
| Hata | §3 |

## 2. Uç noktalar

Rol: **Y** = yönetici, **D** = depo, **Ü** = üretim, **K** = kalite, **M** = mağaza, **S** = satış (telefon).
Okuma uçlarının çoğu bütün web rollerine (Y, D, Ü, K, M) açıktır; yazma uçları işi yapan role ve yöneticiye.
Yönetici şifreyi sıfırladıysa kullanıcı yeni şifresini belirleyene kadar iş uçları `403 PASSWORD_CHANGE_REQUIRED` döner.

### Kimlik ve sistem

| Yöntem | Yol | Rol | Açıklama |
|---|---|---|---|
| POST | `/auth/login` | — | Kullanıcı adı + parola → belirteç, rol, araç deposu |
| GET | `/auth/me` | Y, S | Oturumdaki kullanıcı |
| POST | `/auth/logout` | Y, S | Oturumu sunucuda kapatır (204); belirteç bundan sonra geçersiz |
| POST | `/auth/change-password` | hepsi | `{current_password, new_password}`; en az 8 karakter, harf + rakam. Diğer oturumlar kapanır |
| GET | `/auth/sessions` | hepsi | Kendi açık oturumlarım: `[{started_at, expires_at, current}]` (belirteç ya da özeti dönmez) |
| POST | `/auth/sessions/close-others` | hepsi | Diğer cihazlardan çıkış: bu oturum dışındakiler hemen kapanır → `{closed}`; denetim kaydı `OTURUMLAR_KAPATILDI` |
| GET, POST | `/users` | Y | Kullanıcı listesi / yeni kullanıcı (geçici şifreyle; satış rolü araç ister) |
| PUT | `/users/{id}` | Y | Ad, rol, aktiflik, araç. Kendini pasifleştiremez; son aktif yönetici kaldırılamaz |
| POST | `/users/{id}/reset-password` | Y | Geçici şifre üretir (`{temporary_password}`), oturumları kapatır |

Hatalı giriş: aynı kullanıcı adı ya da adres için 5 dakikada 10 deneme; sonra `429 TOO_MANY_ATTEMPTS`.
| GET | `/health` | — | Servis ve veritabanı durumu |

### Ana veriler (FR-101, FR-201, FR-202, FR-301)

| Yöntem | Yol | Rol | Açıklama |
|---|---|---|---|
| GET, POST | `/products` | Y (GET: Y, S) | Ürün kartları |
| GET, PUT | `/products/{id}` | Y | — |
| GET, POST | `/partners` | Y | Tedarikçi, müşteri, dış üretici; `?role=customer` |
| GET, PUT | `/partners/{id}` | Y | — |
| GET | `/warehouses` | Y | Depolar |
| GET, POST | `/cutting-recipes` | Y | Parçalama reçeteleri ve satırları |
| GET | `/cutting-recipes/{id}` | Y | — |

### Alış, lot ve stok (FR-102–104, FR-112, FR-203, FR-207)

| Yöntem | Yol | Rol | Açıklama |
|---|---|---|---|
| POST | `/purchases` | Y | Alış belgesi; her satır yeni lot + `ALIS_GIRIS`. Fatura ≠ miktar × fiyat ise açıklama ister. |
| GET | `/purchases`, `/purchases/{id}` | Y | — |
| GET | `/lots` | Y | `?product_id=&status=&warehouse_id=&q=` |
| GET | `/lots/{lot_no}` | Y | Lot ayrıntısı: köken, tedarikçi, durum, kalan miktar/değer, birim maliyet, depo bakiyeleri, bir düzey ebeveyn/çocuk |
| GET | `/lots/{lot_no}/movements` | Y | Lotun bütün hareketleri (geçmişe dönük inceleme): zaman, tür, depo, miktar, değer, belge türü + numarası (`doc_no`), kullanıcı (`user_name`; örnek kayıtlarda boş) |
| GET | `/stock` | Y | `?warehouse_id=&product_id=` lot × depo bakiyeleri (sıfır olmayanlar), lot durumu, SKT, birim maliyet |

### Transfer, fire, ters kayıt (FR-303, NFR-002)

| Yöntem | Yol | Rol | Açıklama |
|---|---|---|---|
| POST | `/transfers` | Y | Depolar arası transfer (ör. araca yükleme) |
| GET | `/transfers` | Y | — |
| POST | `/adjustments` | Y | Stok firesi / imha |
| POST | `/movements/{id}/reverse` | Y | Hatalı hareketin ters kaydı (gerekçe zorunlu) |

### Dış üretim ve yeniden işleme (FR-105–111, FR-501, FR-502)

| Yöntem | Yol | Rol | Açıklama |
|---|---|---|---|
| POST | `/production-orders` | Y | Emir + planlanan girdiler; **Model A tahmini kaydedilir ve döner** |
| GET | `/production-orders`, `/production-orders/{id}` | Y | Emir, girdiler, maliyet dökümü, EKP/VKP/kâr/marj, tahmin–gerçek–sapma, miktar farkları |
| POST | `/production-orders/{id}/ship` | Y | Girdileri dış üretici deposuna sevk |
| POST | `/production-orders/{id}/complete` | Y | Mamul kabulü (§4.1) |
| POST | `/production-orders/{id}/cancel` | Y | Yalnız `TASLAK`; `SEVK_EDILDI` ise önce iade transferi |

### Parçalama (FR-201–208, FR-503, FR-504)

| Yöntem | Yol | Rol | Açıklama |
|---|---|---|---|
| POST | `/cuttings` | Y | Taslak: reçete + giriş lotu + giriş kg (+ isteğe bağlı yöntem); her satırda referans beklenti (`standard_kg` = standart oran × giriş); **Model B tahmini T-21'de** |
| GET | `/cuttings`, `/cuttings/{id}` | Y | — |
| PUT | `/cuttings/{id}` | Y | Fiili kg'lar `{"method"?, "outputs": [{"recipe_line_id", "actual_qty"}]}` (taslakta; boş = tartılmadı) |
| POST | `/cuttings/{id}/preview` | Y | PUT ile aynı gövde; denge + dağıtım ön izlemesi, **hiçbir şey kaydetmez** (§4.2) |
| POST | `/cuttings/{id}/approve` | Y | Eksik tartım → `VALIDATION_ERROR`; denge yok → `WEIGHT_IMBALANCE` (fark `details`'te); yoksa deftere yazar, parça lotlarını (`<lot öneki>-<parçalama no>`) açar |

### Satış, iade, ikinci kademe (FR-401, FR-308)

| Yöntem | Yol | Rol | Açıklama |
|---|---|---|---|
| POST | `/sales` | Y, M | Mağaza satışı (ana depodan): `{customer_id, warehouse_id, payment_method, lines: [{lot_no, qty, unit_price?}]}`. Fiyat boşsa ürünün liste fiyatı. Geri çağrılmış lot → `LOT_BLOCKED`, son kullanma tarihi geçmiş lot → `VALIDATION_ERROR` |
| GET | `/sales?day=`, `/sales/{id}` | web | Satış; `seller_name`, `payment_method` (NAKIT, KART, HAVALE, VERESIYE) |
| POST | `/returns` | Y | Müşteri iadesi |
| GET, POST | `/sale-lines/{id}/onward-deliveries` | Y | Müşterinin bildirdiği ikinci kademe teslimatlar |

### İzleme ve geri çağırma (FR-304–310)

| Yöntem | Yol | Rol | Açıklama |
|---|---|---|---|
| GET | `/trace/forward/{lot_no}` | Y | İleri izleme (§4.3) |
| GET | `/trace/backward/{lot_no}` | Y | Geri izleme: kaynak lotlar, tedarikçiler, üretim emirleri, parçalamalar |
| POST | `/recalls` | Y | Geri çağırma başlat: etkilenen bütün lotlar bloke |
| GET | `/recalls`, `/recalls/{id}` | Y | Etkilenen lotlar, alıcılar, miktarlar, satış belgeleri, iletişim, ihlaller |
| GET | `/recalls/{id}/export.csv` | Y | İletişim listesi dosyası |
| POST | `/recalls/{id}/close` | Y | Kapat: `IMHA` veya `SERBEST` |
| GET | `/alerts` | Y | Uyarılar (ör. geri çağırma ihlali) |
| POST | `/alerts/{id}/ack` | Y | Uyarıyı okundu işaretle |

### Raporlar (FR-601–607)

| Yöntem | Yol | Rapor |
|---|---|---|
| GET | `/reports/purchases` | Alış |
| GET | `/reports/production` | Üretim (EKP, farklar, tahmin–gerçek) |
| GET | `/reports/cuttings` | Parçalama (dağıtım, fire, tahmin–gerçek) |
| GET | `/reports/lot-movements` | Lot hareketleri ve bakiyeler |
| GET | `/reports/sales` | Satış (maliyet, brüt kâr) |
| GET | `/reports/recalls` | Geri çağırma |
| GET | `/reports/integrity` | Bütünlük: değişmezler I-1…I-8 (`data_model.md` §5) |

Hepsi `?date_from=&date_to=&product_id=&lot_no=&format=csv` süzgeçlerini kabul eder (uygun olanları).

### Yapay zekâ (FR-501–507)

| Yöntem | Yol | Rol | Açıklama |
|---|---|---|---|
| POST | `/ai/production-forecast` | Y | Kayıt açmadan Model A tahmini |
| POST | `/ai/cutting-forecast` | Y | Kayıt açmadan Model B tahmini |
| GET | `/ai/evaluation` | Y | Model sürümleri, eğitim verisi özeti, referans ve model hataları |

### Senkronizasyon (FR-403–405, TR-007)

| Yöntem | Yol | Rol | Açıklama |
|---|---|---|---|
| POST | `/sync/push` | S | Bekleyen satışları gönder (§4.4); satışta isteğe bağlı `payment_method`. Çevrimdışı satılan geri çağrılmış ya da son kullanma tarihi geçmiş lot kaydedilir, uyarı düşer |
| GET | `/sync/pull?since=N` | S | N'den sonra değişen ürün, müşteri, lot, araç stoku (§4.4) |
| GET | `/sync/day-end?day=` | S | Satış elemanının kendi gün sonu (aşağıdaki biçimde) |

### Günlük işler (gerçek kullanım)

| Yöntem | Yol | Rol | Açıklama |
|---|---|---|---|
| GET | `/dashboard` | web | Ana sayfa: 3 gün içinde dolan / süresi geçmiş lotlar, kritik stok altındaki ürünler, açık geri çağırmalar, okunmamış uyarı, bekleyen emir ve parçalama, bugünkü satış, stok değeri |
| GET | `/day-end?day=&user_id=&warehouse_id=` | Y, M | Gün sonu: satış, iade (geri ödenecek tutar), net; ödeme türüne ve satıcıya göre toplamlar; tek depo istenirse kalan mal. Gün işletmenin yerel günüdür (`BUSINESS_UTC_OFFSET_HOURS`, varsayılan 3) |
| POST | `/stock-counts` | Y, D, S | Sayım: `{warehouse_id, note?, lines: [{lot_no, counted_qty}]}`. Eksik çıkan "Sayım farkı" firesiyle düşülür; fazlası stoka eklenmez, raporlanır. Satış elemanı yalnız kendi aracını sayar |
| GET | `/stock-counts`, `/stock-counts/{id}` | web | Sayım belgeleri, satır farkları ve eksik maliyeti |

### Alarm, denetim, e-posta, panel ve hesaplayıcılar (28 Ekim 2026, ikinci tur)

| Yöntem | Yol | Rol | Açıklama |
|---|---|---|---|
| GET | `/alerts?only_open=&severity=&limit=` | web | Alarmlar; `severity` (BILGI/UYARI/KRITIK), `kind_label`, `can_acknowledge`, okundu işaretleyenin adı. Art arda hatalı giriş alarmı yalnız yöneticiye görünür |
| GET | `/alerts/summary` | web | Zil: açık alarm sayıları (kritik/uyarı) ve son beş açık alarm |
| POST | `/alerts/{id}/ack`, `/alerts/ack-all` | web | Okundu işaretle; kim işaretleyebilir türe göre (ör. fiyat artışı: yönetici, depo; verim: yönetici, kalite, üretim) |
| POST | `/alerts/run-rules` | Y | Kural motorunu şimdi çalıştırır; yeni alarmlar ve taranan kayıt sayısı döner |
| GET / PUT | `/settings/alarm-thresholds` | web / Y | Eşikler: `yield_z`, `price_increase_pct`, `failed_logins` (metin olarak ondalık) |
| GET | `/audit?q=&severity=&username=&day_from=&day_to=&limit=` | Y | Denetim günlüğü (yeniden eskiye) |
| GET | `/audit/export.csv` | Y | Aynı süzgeçle CSV |
| GET | `/mail/status` | web | SMTP tanımlı mı, sunucu ve gönderen adresi (şifre dönmez) |
| GET | `/mail/recipients` | web | E-postası tanımlı kullanıcılar ve cari kartlar |
| POST | `/mail` | web | `{recipients[], subject, body}` giden kutusuna yazılır (en çok 20 alıcı). Alıcı yalnız aktif kullanıcı, kayıtlı cari (müşteri, tedarikçi, dış üretici) ya da `ALLOWED_EMAIL_DOMAINS` (değilse 422, `details.rejected`); kullanıcı başına dakikada 5 gönderim, rapor e-postasıyla ortak sayaç (429) |
| POST | `/mail/batch` | web | `{messages: [{recipients[], subject, body}] (1..50)}`: ayrı ayrı e-postalar, **tek gönderim** sayılır (ör. her müşteriye kendi miktarını içeren geri çağırma bildirimi). Aynı alıcı kuralı; biri geçersizse hiçbiri kaydedilmez |
| GET | `/mail/outbox` | web | Yönetici hepsini, diğerleri kendi gönderdiklerini görür |
| POST | `/mail/deliver`, `/mail/{id}/retry` | Y | Kuyruktakileri şimdi gönder (SMTP yoksa `INVALID_STATE`); hatalıyı yeniden kuyruğa al |
| GET | `/dashboard/charts` | web | Panel grafikleri: EKP geçmişi ve kayıtlı model tahmini, sentetik model testi, hedef/gerçekleşen, maliyet kalemleri, parça maliyeti, sevkiyat |
| POST | `/calc/ekp` | web | Kayıtsız EKP hesabı (gerçek kayıtla aynı fonksiyonlar), kâr/marj ve uyarılar |
| POST | `/calc/cutting` | web | Kayıtsız parçalama maliyet dağıtımı, fire, ağırlık dengesi |
| POST | `/purchases/parse-text` | Y, D | Fatura/irsaliye metninden mal kabul önerisi; hiçbir şey kaydetmez |
| POST | `/reports/{code}/email` | web | `{recipients[1..20], note?}` + `GET /reports/{code}` süzgeçleri → **202**: rapor CSV ekiyle giden kutusuna; alıcı aktif kullanıcı ya da `ALLOWED_EMAIL_DOMAINS` (değilse 422, `details.rejected`); kullanıcı başına dakikada 5 (429) |
| GET / PUT | `/alerts/subscriptions` | web | Kendi alarm e-postası aboneliklerim: `{email, subscriptions: [{alert_type, label, enabled, is_default}]}`; PUT `{subscriptions: [{alert_type, enabled}]}` yalnız gönderilenleri değiştirir; görülemeyen tür 422 |

Hatalı giriş `401 UNAUTHORIZED` olarak yanıtlanır ama yanıt hata fırlatılmadan döner: denetim kaydı ve gerekirse alarm kalıcı olur. Mağazada bloke lot satışı `409 LOT_BLOCKED` döner; satışın yarım yazılanları geri alınır, alarm kalır.

## 3. Hata biçimi ve kodları

Ek kodlar (28 Ekim): `CONFLICT` (409, aynı anda değişen kayıt / benzersizlik), `TOO_MANY_ATTEMPTS` (429), `PASSWORD_CHANGE_REQUIRED` (403), `INTERNAL_ERROR` (500, ayrıntı istemciye verilmez).

```json
{
  "error": {
    "code": "LOT_BLOCKED",
    "message": "SUC-2026-045 lotu geri çağırma nedeniyle bloke; satılamaz.",
    "details": {"lot_no": "SUC-2026-045", "recall_no": "GC-2026-001"}
  }
}
```

| Kod | HTTP | Ne zaman |
|---|---|---|
| `VALIDATION_ERROR` | 422 | Şema/alan doğrulaması (eksi miktar, eksik alan…) |
| `AMOUNT_MISMATCH_NOTE_REQUIRED` | 422 | Fatura tutarı ≠ miktar × fiyat ve açıklama yok (FR-207) |
| `UNAUTHORIZED` | 401 | Belirteç yok veya geçersiz |
| `FORBIDDEN` | 403 | Rol yetmiyor; satış elemanı başka depoya yazmaya çalışıyor |
| `NOT_FOUND` | 404 | Kayıt yok |
| `INSUFFICIENT_STOCK` | 409 | Depo/lot bakiyesi yetmiyor (NFR-004) |
| `LOT_BLOCKED` | 409 | Bloke lotla yasak işlem (FR-310) |
| `WEIGHT_IMBALANCE` | 409 | Parçalamada ağırlık dengesi tolerans dışında (FR-205) |
| `INVALID_STATE` | 409 | Durum akışına aykırı işlem (ör. sevk edilmemiş emri tamamlamak) |
| `DUPLICATE_LOT_NO` | 409 | Lot numarası zaten var |

## 4. Örnek akışlar

Örneklerdeki tahmin değerleri yalnızca biçimi göstermek içindir.

### 4.1 Mamul kabulü — `POST /production-orders/{id}/complete`

İstek:

```json
{
  "received_qty": "85",
  "output_lot_no": "SUC-2026-045",
  "inputs": [
    {"lot_no": "ET-2026-001", "consumed_qty": "100", "returned_qty": "0"},
    {"lot_no": "BAH-2026-014", "consumed_qty": "2", "returned_qty": "0"},
    {"lot_no": "BAG-2026-007", "consumed_qty": "5", "returned_qty": "0"}
  ],
  "service_invoice_no": "FSN-2026-310",
  "service_amount": "467.50"
}
```

Yanıt (özet):

```json
{
  "order_no": "URT-2026-045",
  "status": "TAMAMLANDI",
  "output_lot": {"lot_no": "SUC-2026-045", "qty": "85", "value": "1543.50"},
  "cost": {"raw_materials": "1076.00", "service": "467.50", "total": "1543.50",
           "ekp": "18.158824", "ekp_display": "18.16"},
  "sales": {"vkp": "24.90", "gross_profit_per_unit": "6.74", "margin_pct": "27.07"},
  "forecast": {"model_version": "A-2026-10-28", "expected_qty": "84.2", "expected_ekp": "18.28",
               "deviation_qty": "0.8", "deviation_ekp": "-0.12"},
  "differences": {"planned_qty": "85", "received_qty": "85",
                  "inputs": [{"lot_no": "ET-2026-001", "shipped": "100", "consumed": "100", "returned": "0"}]}
}
```

### 4.2 Parçalama ön izlemesi — `POST /cuttings/{id}/preview`

```json
{
  "input": {"lot_no": "KUZU-2026-012", "qty": "25", "total_cost": "351.00"},
  "balance": {"outputs_kg": "25.000", "difference_kg": "0.000", "tolerance_kg": "0.200", "ok": true},
  "method": "DEGER",
  "lines": [
    {"product": "But",     "actual_kg": "7", "predicted_kg": "6.8", "allocated_cost": "123.41", "cost_per_kg": "17.63"},
    {"product": "Sırt",    "actual_kg": "4", "predicted_kg": "4.1", "allocated_cost": "83.34",  "cost_per_kg": "20.84"},
    {"product": "Omuz",    "actual_kg": "5", "predicted_kg": "5.2", "allocated_cost": "72.12",  "cost_per_kg": "14.42"},
    {"product": "Kaburga", "actual_kg": "3", "predicted_kg": "2.9", "allocated_cost": "33.66",  "cost_per_kg": "11.22"},
    {"product": "Kıyma",   "actual_kg": "3", "predicted_kg": "3.1", "allocated_cost": "38.47",  "cost_per_kg": "12.82"},
    {"line_type": "FIRE",  "actual_kg": "3", "predicted_kg": "2.9", "allocated_cost": "0.00"}
  ],
  "allocated_total": "351.00"
}
```

### 4.3 İleri izleme — `GET /trace/forward/ET-2026-001` (kısaltılmış; tam alanlar `docs/openapi.json` → `TraceOut`)

```json
{
  "source": {"lot_no": "ET-2026-001", "product": "Et", "supplier": "Örnek Et Tedarik", "status": "BLOKE"},
  "lots": [
    {"lot_no": "ET-2026-001",  "depth": 0, "remaining_qty": "0"},
    {"lot_no": "SUC-2026-045", "depth": 1, "remaining_qty": "0"}
  ],
  "links": [{"parent_lot_no": "ET-2026-001", "child_lot_no": "SUC-2026-045", "qty": "100", "process": "URETIM", "doc_no": "URT-2026-045"}],
  "stock": [],
  "recipients": [
    {"customer": "Market A", "lot_no": "SUC-2026-045", "qty": "30",
     "sales": [{"sale_no": "SAT-2026-0101", "sale_line_id": 1, "channel": "ANDROID", "qty": "30", "returned_qty": "0"}],
     "contact": {"person": "…", "phone": "…", "email": "…"}, "onward_status": "BILINMIYOR", "onward_items": []},
    {"customer": "Market B", "lot_no": "SUC-2026-045", "qty": "25", "sales": [{"sale_no": "SAT-2026-0102", "qty": "25"}],
     "contact": {"person": "…", "phone": "…", "email": "…"},
     "onward_status": "KAYITLI", "onward_items": [{"recipient": "Market B Şube 1", "qty": "15"},
                                                  {"recipient": "Market B Şube 2", "qty": "10"}]},
    {"customer": "Market C", "lot_no": "SUC-2026-045", "qty": "30", "sales": [{"sale_no": "SAT-2026-0103", "qty": "30"}],
     "contact": {"person": "…", "phone": "…", "email": "…"}, "onward_status": "BILINMIYOR", "onward_items": []}
  ]
}
```

### 4.4 Senkronizasyon

`POST /sync/push` isteği:

```json
{
  "device_id": "arac-01-pixel",
  "sales": [
    {"client_uuid": "6f1c2a52-6a0e-4c8e-9d7c-1b0e9b1f0a01", "customer_id": 12, "warehouse_id": 3,
     "sold_at": "2026-10-27T10:12:00+03:00",
     "lines": [{"lot_no": "SUC-2026-045", "qty": "30", "unit_price": "24.90"}]}
  ]
}
```

Yanıt:

```json
{
  "results": [
    {"client_uuid": "6f1c2a52-6a0e-4c8e-9d7c-1b0e9b1f0a01", "status": "ACCEPTED", "sale_no": "SAT-2026-0101",
     "warnings": []}
  ]
}
```

Kurallar (T-15): her satış kendi alt işleminde yazılır; biri reddedilirse yalnız o geri alınır, numara boşa harcanmaz. `warehouse_id` kullanıcının araç deposu değilse bütün istek `FORBIDDEN`. Bir gönderimde en çok 200 satış, satışta en çok 50 satır.

Durumlar: `ACCEPTED`, `ACCEPTED_WITH_WARNING` (ör. çevrimdışıyken geri çağrılmış lot satıldı — kaydedildi, ihlal işaretlendi; ya da birim fiyat ürünün liste fiyatının altında — kaydedildi, denetim günlüğüne `LISTE_ALTI_FIYAT` uyarısı yazıldı; aynı kural mağaza satışında da geçerli), `DUPLICATE` (daha önce kaydedilmiş; ilk sonuç döner), `REJECTED` (ör. `INSUFFICIENT_STOCK`; `error` alanıyla).

`GET /sync/pull?since=1840` yanıtı:

```json
{
  "dataset_id": "16d30143-cfa1-11f1-a6f8-8e27a966419b",
  "next_since": 1852,
  "products":  [{"id": 5, "code": "NARIN-SUCUK", "name": "Narin Sucuk 1 kg", "base_unit": "ADET",
                 "unit_weight_kg": "1.000", "sale_price": "24.90", "active": true}],
  "customers": [{"id": 6, "code": "M-A", "name": "Market A", "contact_person": "Ayşe Demir",
                 "phone": "+90 000 000 03 01", "email": "market-a@example.com", "address": "İzmir"}],
  "lots":      [{"id": 9, "lot_no": "SUC-2026-045", "product_id": 5, "expiry_date": "2026-12-20", "status": "BLOKE"}],
  "stock":     [{"lot_id": 9, "qty": "0.000"}]
}
```

Yalnız `SATIS` rolü ve araç deposu atanmış kullanıcı çekebilir (aksi hâlde `FORBIDDEN`). `since=0` ilk çekiştir. Lotlar, araç deposunda bakiyesi olanlarla sınırlıdır; lotun kendisi (ör. bloke edildi) ya da bakiyesi değişince yeniden gelir.

`dataset_id` veritabanının kimliğidir; şema sıfırdan kurulunca değişir. Cihaz kayıtlı kimlikten farklı bir kimlik görürse ya da `next_since` gönderdiği `since` değerinden küçükse (sunucu sıfırlandı veya eski bir yedekten döndü) yerel kopyasını `since=0` ile baştan kurar; aksi hâlde sunucuda artık olmayan kayıtlar cihazda kalırdı.
