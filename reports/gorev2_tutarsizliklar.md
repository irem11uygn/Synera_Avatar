# Görev 2 — Örnek Görseldeki Tutarsızlıklar ve Çözümümüz

| | |
|---|---|
| Takım | Synera |
| Tarih | 27 Ekim 2026 |
| Şartname maddesi | Görev 2: "Örnek görseldeki tutarsızlıkları tespit edin ve açıklayın" |
| Gereksinim | CR-012, FR-203, FR-205, FR-206, FR-207 |

## 1. Not: görsel PDF'te yok

Yarışma e-postalarıyla gelen şartname PDF'inin üç kopyası birebir aynı dosyadır (aynı SHA-256 özeti) ve hiçbirinde gömülü görsel yoktur. Ancak şartname iki tutarsızlığın rakamlarını metinde veriyor:
- 25 kg × 11,50 € = 287,50 € olması gerekirken 351,00 € yazıyor.
- Parçaların toplamı 22 kg.

Aşağıdaki açıklama bu iki rakama dayanır. Görsel bize ulaştırılırsa bu belge gerçek rakamlarla güncellenir.

## 2. Tutarsızlık 1 — Tutar: 287,50 € ≠ 351,00 € (fark 63,50 €)

**Tespit:** 25 kg × 11,50 €/kg = **287,50 €**; görseldeki toplam **351,00 €**.

**Olası nedenler:**

| Olasılık | Hesap | Değerlendirme |
|---|---|---|
| (a) 351,00 € **gerçek toplam alış maliyetidir**: mal bedeline kesim, nakliye ya da veteriner gibi ek masraflar eklenmiştir | 287,50 + 63,50 = 351,00 | Şartname "gerçek toplam alış maliyeti" diyor; en tutarlı açıklama bu |
| (b) Birim fiyat yanlış yazılmıştır | 351,00 / 25 = 14,04 €/kg | Mümkün; ama o zaman 11,50 € hiçbir yere bağlanmıyor |
| (c) Ağırlık yanlış yazılmıştır | 351,00 / 11,50 = 30,52 kg | Küsuratlı ağırlık; parçalar 22 kg tuttuğu için düşük olasılık |

**Sistemimizin cevabı:**
- **Maliyet kalem kalem girilir (FR-203):** fatura tutarı ve ek maliyet kalemleri (kesim, nakliye, veteriner, diğer) ayrı ayrı yazılır. Lot değeri = fatura + ek maliyetler.
- **Fatura ile miktar × birim fiyat uyuşmazsa açıklama zorunludur (FR-207):** Sistem farkı gösterir, açıklama yazılmadan kayıt alınmaz. Veritabanında da kural olarak (`mismatch_needs_note`) korunur.
- **Demo verisinde (a) yorumu uygulanır:** KUZU-2026-012 alışında mal bedeli 25 kg × 11,50 € = 287,50 €, üstüne 63,50 € kesim + nakliye eklenir; lot değeri **351,00 €** olur. Alış raporunda bu satır "Fatura 287,50 € · Ek maliyet 63,50 € · Lot değeri 351,00 €" olarak görünür.

## 3. Tutarsızlık 2 — Ağırlık: parçalar 22 kg ≠ giriş 25 kg (fark 3 kg, %12)

**Tespit:** Görseldeki parçalar toplam 22 kg; giriş 25 kg. 3 kg nereye gittiği belirtilmemiş.

**Olası neden:** Fire ya da yan ürün (kemik, yağ, kesim kaybı) kaydedilmemiştir. Kuzu parçalamada %10–15 kayıp olağandır. Reçetemizde standart fire oranı %12'dir; tam olarak bu farka denk gelir.

**Sistemimizin cevabı:**
- **Ağırlık dengesi kuralı (FR-205):** Giriş = parçalar + yan ürünler + fire, reçetedeki tolerans içinde (0,200 kg) olmalıdır. Fire satırı tartılmadan ya da fark açıklanmadan parçalama **onaylanmaz**. Sunucu `WEIGHT_IMBALANCE` hatası verir ve farkı gösterir.
- **Fire maliyet taşımaz:** Fire satırına maliyet dağıtılmaz; toplam maliyet satılabilir parçalara dağıtılır. Böylece 3 kg kaybın maliyeti kaybolmaz, sağlam ürünlerin birim maliyetine yansır.
- **Dağıtılan toplam = toplam maliyet, kuruşu kuruşuna (FR-206):** Yuvarlamadan doğan kuruş farkı en büyük kalan yöntemiyle kapatılır.

## 4. Demo verisinde sonuç (PRC-2026-012)

Giriş KUZU-2026-012, 25 kg, toplam maliyet 351,00 €, değere göre dağıtım:

| Kalem | Fiili kg | Dağıtılan maliyet | Maliyet / kg | Parça lotu |
|---|---|---|---|---|
| But | 7,000 | 123,41 € | 17,63 € | BUT-PRC-2026-012 |
| Sırt | 4,000 | 83,34 € | 20,84 € | SIRT-PRC-2026-012 |
| Omuz | 5,000 | 72,12 € | 14,42 € | OMUZ-PRC-2026-012 |
| Kaburga | 3,000 | 33,66 € | 11,22 € | KABURGA-PRC-2026-012 |
| Kıyma | 3,000 | 38,47 € | 12,82 € | KIYMA-PRC-2026-012 |
| Fire | 3,000 | 0,00 € | — | — |
| **Toplam** | **25,000** | **351,00 €** | | |

- Parçalar 22 kg + fire 3 kg = giriş 25 kg: denge tutuyor.
- Dağıtılan toplam 351,00 € = toplam maliyet.
- Miktara göre dağıtım da seçilebilir. O zaman her kilo 15,95 € taşır; düz yuvarlama toplamı 350,99 € yapar, eksik 1 kuruş en büyük kalanlı satıra eklenir ve toplam yine 351,00 € olur.
- Bu rakamlar otomatik testlerle de denetlenir: `backend/tests/test_cutting.py` (AT-03, AT-04).

## 5. Nerede görülür

| Yer | Ne görünür |
|---|---|
| Web → Hammadde alışları → KUZU-2026-012 | Fatura, ek maliyet kalemleri, lot değeri 351,00 € |
| Web → Parçalama → PRC-2026-012 | Ağırlık dengesi (25 = 22 + 3), dağıtım, parça lotları, standart oran ve YZ tahmini |
| Web → Raporlar → Alış raporu / Parçalama raporu | Aynı rakamlar, süzgeç ve CSV ile |
