# Yapay Zekâ Değerlendirme Raporu

| | |
|---|---|
| Takım | Synera |
| Tarih | 27 Ekim 2026 |
| Modeller | A — üretim verimi ve EKP tahmini (`A-1.0.0`) · B — parçalama verimi tahmini (`B-1.0.0`) |
| Karşıladığı maddeler | Şartname §4; FR-501…FR-507, TR-006, CR-006 |
| Kod | `ml/avatar_ml/` (veri, özellikler, eğitim, tahmin) · `backend/app/services/ai.py` (sunucuya bağlantı) |
| Ölçümlerin kaynağı | `ml/models/metadata.json` (eğitim komutunun yazdığı dosya; bu belgedeki bütün sayılar oradan) |

## 1. Özet

| | Referans yöntem | Model | İyileşme |
|---|---|---|---|
| **Model A** — paket sayısı ortalama mutlak hatası | 1,81 paket | **1,23 paket** | %32 |
| Model A — EKP ortalama mutlak hatası | 0,20 € | **0,13 €** | %38 |
| Model A — EKP ortalama yüzde hatası | %1,09 | **%0,69** | %37 |
| **Model B** — parça başına ortalama mutlak hata | 0,21 kg | **0,14 kg** | %36 |
| Model B — ortalama yüzde hata | %5,19 | **%3,36** | %35 |

Ölçüm, eğitimde hiç kullanılmamış en yeni %20'lik veride yapıldı (48 üretim emri, 60 parçalama). İki model de referans yöntemi geçti. Bu sonuç **sentetik veride** alındı; gerçek işletmede aynı başarının kanıtı değildir (§7).

Zorunlu senaryoda (URT-2026-045, sistemde kayıtlı tahmin):

| Kalem | Tahmin (emir açılırken) | Gerçek (kabulde) | Sapma |
|---|---|---|---|
| Paket sayısı | 84 | 85 | +1 |
| EKP | 18,31 € | 18,16 € | −0,15 € |

## 2. Neyi tahmin ediyoruz, neden

**Model A — dış üretim:** Emir açılırken et miktarı, dış üretici, tedarikçi, etin bekleme süresi, baharat ve bağırsak oranı ve ay bilinir. Bilinmeyen tek şey kaç paket çıkacağıdır. Model **et bazlı verimi** (mamul kg / et kg) tahmin eder. Paket sayısı ve EKP bundan hesaplanır:

- Beklenen paket = ⌊et kg × tahmini verim / paket ağırlığı⌋
- Tahmini EKP = (hammadde değeri + hizmet ücreti × beklenen paket) / beklenen paket

Hammadde değeri tahmin değildir. Planlanan lotların bugünkü defter değeridir (senaryoda 970 + 48 + 58 = 1.076 €). Böylece EKP'deki belirsizlik yalnız verimden gelir ve hata nereden geliyor açıkça görülür.

**Model B — parçalama:** Parçalama açılırken tür, karkas ağırlığı, tedarikçi ve ay bilinir. Model altı payı tahmin eder: but, sırt, omuz, kaburga, kıyma, fire. Paylar toplamı 1 olacak biçimde ölçeklenir ve giriş ağırlığıyla çarpılır. Böylece tahmin edilen parçalar ve fire, toplamda girişe eşit olur; ağırlık dengesi tahminde de korunur.

## 3. Veri

Gerçek işletme verisi olmadığı için **sabit tohumlu sentetik veri** ürettik (`ml/avatar_ml/data_gen.py`, tohum 2026). Her etki kodda ve aşağıda açıkça yazılıdır. Aynı komut her çalıştırmada aynı veriyi üretir.

| Veri | Satır | Dönem | Dosya |
|---|---|---|---|
| Dış üretim emirleri | 240 | 2 Kasım 2024 – 15 Ekim 2026 | `data/synthetic/production_history.csv` |
| Parçalamalar | 300 | Aynı dönem | `data/synthetic/cutting_history.csv` |

**Model A'nın verimine etki eden varsayımlar:**

| Etken | Varsayım |
|---|---|
| Taban verim | 0,862 |
| Dış üretici | FSN-01: 0 · FSN-02: −0,020 · FSN-03: +0,012 |
| Et tedarikçisi | TED-ET: 0 · TED-ET-2: −0,015 · TED-ET-3: +0,006 |
| Yaz kuruması | Temmuz'da en çok −0,010 (mevsimsel) |
| Etin bekleme süresi | 2 günden sonraki her gün −0,004 |
| Küçük parti kaybı | −1,2 / et kg (100 kg'da −0,012) |
| Gözlenmeyen etkenler | Normal dağılım, standart sapma 0,010 (yağ oranı, makine ayarı vb.) |

**Model B'nin parça paylarına etki eden varsayımlar:**

| Etken | Varsayım |
|---|---|
| Tür tabanı | Kuzu: reçetedeki standart oranlar (0,27 / 0,17 / 0,20 / 0,12 / 0,12 / 0,12); koyun ve keçi için ayrı tabanlar |
| Karkas ağırlığı | Türün ortalamasından ağır karkasta but ve sırt payı düşer, kıyma ve fire artar |
| Tedarikçi | TED-KUZU-2: fire +0,010, but −0,010 |
| Bahar kuzusu (Mart–Haziran) | Fire −0,010, but +0,010 |
| Gözlenmeyen etkenler | Her pay × exp(N(0; 0,04)), sonra toplam 1'e ölçeklenir |

Senaryo koşulunda (FSN-01, TED-ET, 100 kg, taze et, Ekim) beklenen verim ≈ 0,850, yani 85 paket. Bu, şartnamedeki rakamla tutarlıdır.

## 4. Yöntem

| Adım | Ne yapıldı |
|---|---|
| Ayırma | Tarihe göre sıralı; ilk %80 eğitim, son %20 test. Gelecekteki bir kayıt geçmişi tahmin etmekte kullanılmaz. |
| Özellikler | Model A: et kg, 1/et kg, baharat ve bağırsak oranı, etin bekleme günü, ayın sinüs ve kosinüsü, dış üretici ve tedarikçi (tek-sıcak). Model B: giriş kg, ayın sinüs ve kosinüsü, bahar göstergesi, tür ve tedarikçi (tek-sıcak). |
| Aday modeller | Ridge (doğrusal, standartlaştırılmış) ve HistGradientBoosting (karar ağacı topluluğu), scikit-learn 1.8.0 (ADR-005) |
| Model seçimi | Eğitim kısmında 5 katlı zaman sıralı çapraz doğrulama; ortalama mutlak hatası düşük olan seçilir |
| Seçilen | İki model için de HistGradientBoosting |
| Ölçüm | Test kısmında model ve referans yöntem aynı satırlarda: MAE (ortalama mutlak hata) ve MAPE (ortalama yüzde hata) |
| Sunulan model | Seçilen yöntem bütün veride yeniden eğitildi; `ml/models/model_a.joblib`, `model_b.joblib` |

Çapraz doğrulamadaki ortalama hata:

| | Ridge | HistGradientBoosting |
|---|---|---|
| Model A (verim) | 0,01140 | **0,00996** |
| Model B (pay) | 0,00590 | **0,00585** |

Model B'de iki yöntem neredeyse eşit çıktı. Paylardaki etkiler büyük ölçüde doğrusal olduğu için bu beklenen bir sonuç.

**Referans yöntemler** (şartnamenin istediği "basit karşılaştırma"):
- Model A: eğitim verisindeki ortalama et bazlı verim (%83,07). Tek mamul olduğu için ürün bazında ortalama ile aynıdır.
- Model B: reçetedeki standart oran × giriş ağırlığı. Uygulamadaki parçalama ekranında "standart kg" sütunu olarak da görünür.

## 5. Sonuçlar (test verisi)

### Model A

| Ölçü | Referans | Model | İyileşme |
|---|---|---|---|
| Verim hatası (yüzde puan) | 1,33 | 1,01 | %24 |
| Paket sayısı MAE | 1,81 | 1,23 | %32 |
| Paket sayısı MAPE | %1,56 | %0,98 | %37 |
| EKP MAE | 0,203 € | 0,127 € | %38 |
| EKP MAPE | %1,09 | %0,69 | %37 |

Test verisinden örnek tahminler (son 8 emir):

| Emir | Dış üretici | Tedarikçi | Et kg | Gerçek paket | Referans | Model | Gerçek EKP | Model EKP |
|---|---|---|---|---|---|---|---|---|
| SYN-URT-0233 | FSN-02 | TED-ET | 80 | 64 | 66 | 63 | 19,30 | 19,52 |
| SYN-URT-0234 | FSN-02 | TED-ET | 185 | 152 | 153 | 153 | 18,48 | 18,40 |
| SYN-URT-0235 | FSN-01 | TED-ET-2 | 215 | 179 | 178 | 180 | 17,73 | 17,66 |
| SYN-URT-0236 | FSN-02 | TED-ET | 155 | 126 | 128 | 126 | 18,70 | 18,70 |
| SYN-URT-0237 | FSN-02 | TED-ET-3 | 90 | 74 | 74 | 74 | 18,09 | 18,09 |
| SYN-URT-0238 | FSN-03 | TED-ET-2 | 75 | 62 | 62 | 62 | 18,43 | 18,43 |
| SYN-URT-0239 | FSN-01 | TED-ET-2 | 110 | 89 | 91 | 89 | 19,23 | 19,23 |
| SYN-URT-0240 | FSN-01 | TED-ET | 135 | 115 | 112 | 114 | 17,93 | 18,04 |

Model, verimi düşük dış üreticide (FSN-02) ve küçük partilerde referanstan belirgin biçimde iyi. Referans her emre aynı ortalama verimi uyguladığı için bu farkları göremiyor.

### Model B

| Parça | Referans MAE (kg) | Model MAE (kg) |
|---|---|---|
| But | 0,292 | 0,188 |
| Sırt | 0,220 | 0,132 |
| Omuz | 0,150 | **0,158** |
| Kaburga | 0,134 | 0,117 |
| Kıyma | 0,218 | 0,110 |
| Fire | 0,260 | 0,108 |
| **Ortalama** | **0,212** | **0,135** |

**Omuzda model referanstan biraz kötü** (0,150 → 0,158 kg). Veride omuz payı ağırlıkla değişmeyecek biçimde üretildi (etkisi 0); model bu satırda yalnız gürültü görüyor. Referansın sabit oranı burada zaten doğru. En büyük kazanç fire ve kıymada: bu ikisi karkas ağırlığı ve tedarikçiyle değişiyor.

Test verisinden örnek parçalama (SYN-PRC-0300, kuzu, 30,33 kg):

| Parça | Gerçek | Referans | Model |
|---|---|---|---|
| But | 8,09 | 8,19 | 8,05 |
| Sırt | 4,83 | 5,16 | 4,95 |
| Omuz | 6,09 | 6,07 | 6,22 |
| Kaburga | 3,68 | 3,64 | 3,67 |
| Kıyma | 3,80 | 3,64 | 3,69 |
| Fire | 3,84 | 3,64 | 3,76 |

## 6. Uygulamaya bağlantı (TR-006)

- **Tahmin iş anında kaydedilir.** Dış üretim emri açılınca Model A, parçalama taslağı açılınca Model B çalışır. Sonuç `ai_forecasts` tablosuna yazılır: model sürümü, kullanılan özellikler, tahmin.
- **Tahmin sonradan değişmez.** Kabulde ya da onayda gerçek sonuç gelince sapma bu kayda göre hesaplanır; gerçek sonuç tahmine sızamaz.
- **Ekranda tahmin, gerçek ve sapma yan yana görünür:**
  - Üretim emri ayrıntısında "YZ tahmini" kartı: beklenen paket, EKP, referans ve sapma.
  - Parçalama ekranında her parça için standart kg, YZ tahmini kg ve gerçek kg.
  - Üretim ve parçalama raporlarında tahmin ve sapma sütunları.
  - "Yapay zekâ" ekranında bu değerlendirme ve sistemdeki gerçek kayıtların karşılaştırması.
- **API uçları:**
  - `POST /ai/production-forecast`: kayıt açmadan tahmin (emir formunda ön izleme).
  - `POST /ai/cutting-forecast`: aynısı, parçalama için.
  - `GET /ai/evaluation`: bu raporun ölçümleri ve gerçek kayıtlarla karşılaştırma.
- **Model yoksa iş durmaz.** Model dosyası yoksa ya da tahmin hata verirse emir ve parçalama yine açılır; tahmin alanı boş kalır, hata günlüğe yazılır. Bu durum otomatik testle denetleniyor (`test_missing_model_never_blocks_the_workflow`).
- **İzleme ve geri çağırma hiçbir yerde tahmin kullanmaz** (CON-003). Lot ilişkileri yalnız kayıtlardan gelir.

## 7. Sınırlılıklar (FR-507)

1. **Veri sentetiktir.** Etkileri biz varsaydık ve koda yazdık. Ölçülen başarı, modelin bu varsayımları ne kadar geri bulabildiğini gösterir; gerçek bir işletmede aynı başarının kanıtı değildir.
2. **Veri küçüktür:** 240 üretim, 300 parçalama. Eğitimde görülmemiş bir dış üretici ya da tedarikçi için model ortalama gibi davranır.
3. **Gözlenmeyen etkenler** (etin yağ oranı, makine ayarı, işçilik) gürültü olarak kalır. Bu yüzden hata sıfıra inmez; referansa göre kazanç sınırlıdır.
4. **Model B'de omuz payı** için model referanstan iyi değil. Gerçek veride de böyle çıkarsa o parça için reçete oranı kullanılmalı.
5. **Gerçek kayıtlar biriktikçe** aynı kodla yeniden eğitilmeli ve referans yöntemle yeniden karşılaştırılmalı. Sistem gerçek tahmin ve sonuçları zaten `ai_forecasts` tablosunda ve emir/parçalama kayıtlarında topluyor.

## 8. Yeniden üretme

Depo kökünden; Docker içinde, Linux'ta:

```bash
docker compose build api
```

```bash
docker compose run --rm --no-deps --user root -v "$PWD:/repo" -w /repo -e PYTHONPATH=/repo/ml api sh -c "python -m avatar_ml.data_gen && python -m avatar_ml.train"
```

Birinci komut veri dosyalarını, ikincisi modelleri ve `metadata.json`'u yeniden yazar. Aynı tohumla aynı veri üretilir. Yapay zekâ paketinin testleri:

```bash
docker compose run --rm --no-deps api sh -c "cd /ml && pytest -q"
```
