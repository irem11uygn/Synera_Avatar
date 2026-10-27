# İki Kişilik İş Bölümü ve Kalan İşler

| | |
|---|---|
| Tarih | 27 Ekim 2026 |
| Son teslim | **1 Kasım 2026 23:59** (hedef: 1 Kasım öğleden sonra) |
| Ekip | Kişi 1 — Caner · Kişi 2 — ekip arkadaşı (adı yazılacak) |
| Dayanak | `requirements.md` (gereksinimler), `development_plan.md` (iş listesi T-xx), `api.md` (uç noktalar), `submission_checklist.md` |

Bu belge, kalan işleri iki kişiye **birbirinin dosyalarına en az dokunacak biçimde** böler. Her iş, karşıladığı gereksinim kimlikleriyle ve "bitti" ölçütüyle yazılmıştır. Bölüşüm bir öneridir; kulvarlar istenirse yer değiştirebilir, ama bir dosyanın bir sahibi olması kuralı kalır.

## 1. Bugünkü durum (27 Ekim)

**Biten işler:** T-01, T-03…T-15 (T-02 açık sorularla sürüyor).

**Çalışanlar:**
- Görev 1 (dış üretim, EKP) ve Görev 2 (parçalama, maliyet dağıtımı) sunucuda ve web'de uçtan uca çalışıyor.
- Android'de satış ve satışların sunucuya gönderimi çalışıyor; çevrimdışı da satış yapılabiliyor.
- Hammadde alışı, stok, lotlar ve lot hareket geçmişi, transfer ekranları hazır.

**Testler:**
- 134 sunucu, 16 web, 17 Android testi geçiyor.
- Çalışan sistemde bütünlük denetimi 8/8 tutarlı.

**Hiç başlanmamış iki büyük blok:** Görev 3 (izleme ve geri çağırma) ve iki yapay zekâ modeli.

## 2. Gereksinim kapsamı

Durum: **Bitti** · **Kısmen** (ne eksik yazılı) · **Eksik** · İsteğe bağlı işler kapsam dışında. "Sahip" sütunu kalan işin sorumlusudur.

### Görev 1 ve ana veriler

| Gereksinim | Durum | Kalan iş | Sahip |
|---|---|---|---|
| FR-101 ürün kartları, FR-103 birimler, FR-301 cariler | Bitti | — | — |
| FR-102 alış, FR-207 fatura farkı | Bitti | — | — |
| FR-104 stok kırılımı | Bitti | — | — |
| FR-105…FR-108, FR-110, FR-111 dış üretim, EKP, kâr/marj | Bitti | — | — |
| FR-109 miktar farkları | Kısmen | Farklar emirde görünüyor; **üretim raporunda** da görünmeli (FR-602) | Kişi 1 |
| FR-112 geçmişe dönük inceleme | Bitti | Lot hareket geçmişi: kim, ne zaman, hangi belge | — |

### Görev 2

| Gereksinim | Durum | Kalan iş | Sahip |
|---|---|---|---|
| FR-201…FR-208 reçete, dağıtım anahtarı, tartım, denge, dağıtım, parça lotları | Bitti | AT-03 ve AT-04 API'de geçti | — |
| CR-012 örnek görseldeki tutarsızlıklar | Kısmen | Analiz `project_analysis.md` §3.3'te; teslim belgesinde ayrı, açık bir bölüm olmalı (görsel PDF'te yok: S-01) | Kişi 1 |

### Görev 3 (izlenebilirlik ve geri çağırma)

| Gereksinim | Durum | Kalan iş | Sahip |
|---|---|---|---|
| FR-302 miktarlı çoktan çoğa lot bağları | Bitti | — | — |
| FR-303 hareket türleri | Kısmen | Var: alış, transfer, üretim, parçalama, satış. **Eksik:** müşteri iadesi, fire/imha, (zaman kalırsa) yeniden işleme | Kişi 1 |
| FR-304 ileri izleme, FR-305 geri izleme | Eksik | Lot ağı servisi hazır (`lot_graph.py`); API ve ekran yok | Kişi 1 |
| FR-306 geri çağırma başlatma, FR-307 liste + dışa aktarma | Eksik | `recalls`, `recall_lots`, `alerts` tabloları hazır | Kişi 1 |
| FR-308 ikinci kademe dağıtım | Eksik | `onward_deliveries` tablosu hazır | Kişi 1 |
| FR-309 zorunlu senaryo örnek kayıtlarla hazır gelir | Kısmen | Senaryo şu an elle kuruluyor. `docker compose up` sonrası ET-2026-001 → URT-2026-045 → SUC-2026-045 → Market A 30 / B 25 / C 30 hazır gelmeli (**demo profili**) | Kişi 1 |
| FR-310 bloke lot hiçbir kanaldan satılamaz/transfer edilemez/üretimde kullanılamaz | Bitti | Defter, Android ve sunucu gönderimi engelliyor; çevrimdışı satış kurallı istisna (AT-12) | — |

### Android satış ve senkronizasyon

| Gereksinim | Durum | Kalan iş | Sahip |
|---|---|---|---|
| FR-401…FR-405, TR-001, TR-002, TR-007 | Bitti | AT-11, AT-12 geçti; emülatörde uçak modu denendi | — |
| NFR-005 Android kullanılabilirlik | Bitti | Videoda gösterilecek | Video |
| FR-406 Android operasyon ekranları | İsteğe bağlı | Plandan çıkarıldı | — |

### Yapay zekâ

| Gereksinim | Durum | Kalan iş | Sahip |
|---|---|---|---|
| FR-505 örnek veri seti ve varsayımlar | Eksik | T-18 sentetik veri üreticisi | Kişi 2 |
| FR-501 Model A, FR-503 Model B | Eksik | T-19, T-20 (Model B için referans "beklenen kg" ekranda zaten var) | Kişi 2 |
| FR-506 referans yöntem ve hata ölçümü, FR-507 sınırlılıklar, CR-006 YZ raporu | Eksik | T-19, T-20 + `reports/ai_degerlendirme.md` | Kişi 2 |
| FR-502, FR-504 tahmin–gerçek–sapma ekranda, TR-006 API entegrasyonu | Eksik | T-21 | Kişi 2 |
| FR-551, FR-552 | İsteğe bağlı | Kapsam dışı (T-24 plandan çıkarıldı) | — |

### Raporlar

| Gereksinim | Durum | Kalan iş | Sahip |
|---|---|---|---|
| FR-601 alış, FR-603 parçalama, FR-604 lot hareketleri, FR-605 satış | Kısmen | Listeler/ayrıntılar var; **rapor ekranları** (süzgeç + CSV) ve `/reports/*` uçları yok | Kişi 1 |
| FR-602 üretim raporu | Kısmen | Rapor + YZ tahmin/sapma sütunu (sütunu Kişi 2'nin tahmin alanı doldurur) | Kişi 1 |
| FR-606 geri çağırma raporu | Eksik | T-16'dan sonra | Kişi 1 |
| FR-607 bütünlük raporu | Kısmen | Denetim servisi var (`integrity.py`); uç ve ekran yok | Kişi 1 |

### Kalite gereksinimleri

| Gereksinim | Durum | Kalan iş | Sahip |
|---|---|---|---|
| NFR-001 parasal doğruluk, NFR-003 işlem bütünlüğü, NFR-004 stok tutarlılığı | Bitti | — | — |
| NFR-002 değişmez defter | Kısmen | Tetikleyiciler ve ters kayıt servisi var; ters kayıt **uç ve düğmesi** yok | Kişi 1 |
| NFR-006 kurulabilirlik | Kısmen | Tek komut çalışıyor. Eksik: demo profili; **temiz bilgisayarda** kurulum testi (AT-14) | Kişi 1 (profil), Kişi 2 (test) |
| NFR-007 güvenlik, NFR-008 denetlenebilirlik, NFR-010 sürdürülebilirlik | Bitti | — | — |
| NFR-009 performans (izleme < 2 sn) | Ölçülmedi | T-23'te ölçülür | Kişi 2 |

### Teslim

| Gereksinim | Durum | Kalan iş | Sahip |
|---|---|---|---|
| CR-007 veri modeli, CR-008 API açıklaması | Bitti | Son güncelleme T-25'te | Kişi 1 |
| CR-009 örnek kayıtlar | Kısmen | Demo profili | Kişi 1 |
| CR-010 otomatik testler | Bitti | Kabul testleri T-23 | Kişi 2 |
| CR-011 üç görev ve iki YZ entegre | Kısmen | Görev 3 + YZ | İkisi |
| CR-001 herkese açık GitHub, CR-005 son commit | Bekliyor | 1 Kasım; GitHub'a gönderim ön izleme ve onayla | Kişi 1 |
| CR-002 video ≤ 15 dk, CR-003 etkilenen marketlerin gösterimi | Bekliyor | T-27 | İkisi |
| CR-004 e-posta | Bekliyor | Kimin göndereceği açık (S-05) | Ekip kararı |

## 3. Kim neyin sahibi (dosya sahipliği)

Aynı dosyada iki kişinin aynı anda çalışması birleştirmede çakışma demektir. Sahibi olmayan dosyaya dokunmadan önce diğerine haber verilir.

| Kişi 1 — Caner: Görev 3, raporlar, entegrasyon | Kişi 2 — arkadaş: yapay zekâ, kabul testleri, kurulum testi |
|---|---|
| `backend/app/services/` (yeni: `trace.py`, `recall.py`, `returns.py`, `adjustments.py`, `reports.py`) ve var olan servisler | `ml/` (bütünü), `data/synthetic/` |
| `backend/app/api/` (yeni: `trace.py`, `recalls.py`, `alerts.py`, `returns.py`, `adjustments.py`, `reports.py`) | `backend/app/services/ai.py`, `backend/app/api/ai.py`, `backend/tests/test_ai*.py` |
| `backend/app/seed.py`, `data/seed/` (demo profili) | `tests/` (kök: uçtan uca kabul testleri) |
| `web/src/pages/` (Görev 3, rapor, uyarı ekranları), `web/src/App.tsx` (menü) | `web/src/components/ForecastCard.tsx` |
| `android/` (gerekirse küçük düzeltmeler), APK üretimi | `reports/ai_degerlendirme.md`, `reports/kabul_testleri.md` |
| `docs/api.md`, `docs/data_model.md`, `docs/architecture.md`, `README.md` | `docs/` içinde YZ bölümleri (Kişi 1'e haber vererek) |

**Ortak ve dikkat isteyen dosyalar** (çakışırsa iki tarafın satırları da tutulur):
- `backend/app/main.py`: yeni yönlendiriciler eklenir.
- `backend/Dockerfile`: Kişi 2, `ml` paketini ve scikit-learn'ü ekler.
- `CHANGELOG.md`, `reports/test_results.md`, `docs/development_plan.md` durum günlüğü: herkes kendi bölümünü sona ekler.
- Üretilen dosyalar (`docs/openapi.json`, `web/src/api/schema.d.ts`) elle birleştirilmez. Birleştirmeden sonra API çalışırken yeniden üretilir (§5).

## 4. İşler

Süreler kaba tahmindir (kişi-saat). "Bitti" ölçütü sağlanmadan iş bitmiş sayılmaz (§7).

### Kişi 1 — Caner

| Sıra | İş | Gereksinim | Bitti ölçütü | Süre |
|---|---|---|---|---|
| 1 | **T-16a** İleri/geri izleme API: `GET /trace/forward/{lot}`, `/trace/backward/{lot}` (`api.md` §4.3 biçimi: türev lotlar, stok, satış belgeleri, alıcılar, iletişim) | FR-304, FR-305 | ET-2026-001 ileri izlemesi SUC-2026-045 ve Market A 30 / B 25 / C 30'u verir; SUC-2026-045 geri izlemesi üç hammadde lotunu, tedarikçileri, URT-2026-045'i verir (AT-06, AT-07 sunucu testi) | 3 |
| 2 | **Demo profili** (`SEED_PROFILE=demo`, varsayılan): `base` + URT-2026-045 kabul + araca yükleme + Android kanalından 30/25/30 satış + örnek parçalama; aynı servislerle (defter kuralları geçerli) | FR-309, CR-009, NFR-006 | `docker compose down -v && docker compose up --build` sonrası senaryo hazır; bütünlük 8/8 | 2 |
| 3 | **T-16b** Geri çağırma: `POST /recalls` (kaynak + bütün türevler bloke), liste, CSV dışa aktarma, kapatma; uyarılar (`/alerts`); çevrimdışı ihlal yapan müşteri listeye eklenir | FR-306, FR-307, FR-310 | AT-08: liste A/B/C'yi miktar + iletişimle verir, CSV iner; bloke sonrası web/API/Android satışı reddeder | 3 |
| 4 | **T-16c** İkinci kademe: `GET/POST /sale-lines/{id}/onward-deliveries`; listede "kesin" ve "bilinen son alıcı, sonrası bilinmiyor" | FR-308 | AT-09 sunucu testi | 1,5 |
| 5 | **T-17** Web: izleme ekranı (tek ekranda zincir + alıcılar), geri çağırma başlat/liste/CSV/kapat, uyarılar | FR-304…FR-308 | ET-2026-001 senaryosu arayüzden yürür | 4 |
| 6 | **Eksik hareketler:** müşteri iadesi (`/returns`), fire/imha (`/adjustments`), ters kayıt (`/movements/{id}/reverse`) + web düğmeleri; zaman kalırsa yeniden işleme | FR-303, NFR-002 | Her biri defter testleriyle; bütünlük 8/8 | 4 |
| 7 | **T-22** Raporlar: `/reports/*` + web rapor ekranları (süzgeç, CSV); FR-607 bütünlük ekranı | FR-601…FR-607, FR-109 | Her rapor demo verisiyle dolu; üretim raporunda tahmin/sapma sütunu (Kişi 2'nin alanı) | 5 |
| 8 | **T-25 (payı)** README son hâli, `api.md`, `data_model.md`, `architecture.md`; CR-012 tutarsızlık bölümü | CR-007, CR-008, CR-012, TR-007 | Belgeler kodla tutarlı | 3 |
| 9 | APK üretimi (`assembleRelease` ya da debug APK) ve depoda yayın | CR-001 | APK telefona/emülatöre kurulup giriş yapılır | 0,5 |
| | **Toplam** | | | ≈ 26 |

### Kişi 2 — ekip arkadaşı

| Sıra | İş | Gereksinim | Bitti ölçütü | Süre |
|---|---|---|---|---|
| 0 | **Kurulum:** paketten depoyu aç, `docker compose up --build`, testleri çalıştır, web'e gir (`BASLA_BURADAN.md`) | — | 134 sunucu + 16 web testi kendi bilgisayarında geçer | 1–2 |
| 1 | **T-18** Sentetik veri üreticisi (`ml/avatar_ml/data_gen.py`): geçmiş dış üretim emirleri (girdi kg'ları, mamul, verim, EKP) ve parçalamalar (tür, giriş kg, parça kg'ları); sabit tohum; varsayımlar `data/synthetic/README.md`'de | FR-505, CON-004 | Aynı tohumla aynı veri; dağılım özeti belgede | 3 |
| 2 | **T-19** Model A (et bazlı verim → beklenen paket ve EKP); referans: ürün bazında geçmiş ortalama verim; kronolojik %80/%20; MAE, MAPE (ADR-005) | FR-501, FR-506 | Test verisinde hata tablosu; model referansla karşılaştırılmış (sonuç ne çıkarsa dürüstçe yazılır) | 4 |
| 3 | **T-20** Model B (parça payları, toplam 1'e ölçeklenir); referans: reçete oranı × giriş ağırlığı | FR-503, FR-506 | Parça bazlı hata tablosu | 4 |
| 4 | **T-21** Entegrasyon (§6'daki sözleşme): `services/ai.py`, `/ai/production-forecast`, `/ai/cutting-forecast`, `/ai/evaluation`; emir/parçalama açılırken tahmin kaydı; web'de "YZ tahmini" kartı (emir ve parçalama ayrıntısında tahmin–gerçek–sapma) | FR-502, FR-504, TR-006, CR-011 | Yeni emirde tahmin görünür; kabulden sonra sapma görünür; model dosyası yoksa iş akışı durmaz | 5 |
| 5 | **YZ raporu** `reports/ai_degerlendirme.md`: yöntem, veri, örnek tahminler, referansla karşılaştırma, hata ölçümü, sınırlılıklar | CR-006, FR-507 | Değerlendirici tek belgede okuyabilir | 2 |
| 6 | **T-23** Kabul testleri: AT-01…AT-12, AT-15 çalışan sisteme karşı otomatik (`tests/`); izleme süresini ölç | CR-010, NFR-009 | `reports/kabul_testleri.md`'de hepsi yeşil; izleme < 2 sn | 6 |
| 7 | **T-26** Temiz kurulum testi **kendi bilgisayarında**: yalnız README adımlarıyla sıfırdan kur | NFR-006, AT-14 | Sorunsuz kuruluyor ya da sorunlar düzeltilmek üzere Kişi 1'e bildirildi | 2 |
| 8 | **T-27 (payı)** Video senaryosu metni ve süre provası (≤ 15 dk) | CR-002, CR-003 | Senaryo ana başlıklarla, dakika dakika | 2 |
| | **Toplam** | | | ≈ 29 |

### Birlikte

| İş | Ne zaman |
|---|---|
| Günlük birleştirme (§5) ve kısa kontrol: testler + bütünlük + ana senaryo | Her akşam |
| T-27 video çekimi (Kişi 1'in bilgisayarında emülatör ve web hazır) | 31 Ekim |
| T-28 teslim: `submission_checklist.md`; GitHub'a gönderim (ön izleme + onay), depo herkese açık, e-posta | 1 Kasım |
| T-02 açık sorular: S-01 (Görev 2 görseli organizatöre soruldu mu?), S-05 (GitHub hesabı, e-postayı kim gönderir), kişi adları | Bugün |

## 5. Birlikte çalışma

**Ortak depo:** Proje bitene kadar GitHub kullanılmıyor (ekip kararı). Kod, **git paketi** (`.bundle` dosyası) ile taşınır. Bu dosya WhatsApp, Drive ya da USB ile gönderilebilir. Kişi 1 birleştirmeden sorumludur; `main` dalı onda tutulur.

Kişi 2 başlangıçta (bir kez):

```bash
git clone AVATAR_Synera.bundle AVATAR_Yarisma
```

```bash
cd AVATAR_Yarisma && git switch -c kisi2
```

Kişi 2 günün işini gönderir (`main`'den sonra yaptığı commit'ler):

```bash
git bundle create kisi2_28ekim.bundle main..kisi2
```

Kişi 1 alır ve birleştirir (`main` dalındayken):

```bash
git fetch ../kisi2_28ekim.bundle kisi2:kisi2 && git merge kisi2
```

Kişi 1 birleşmiş `main`'i geri gönderir:

```bash
git bundle create main_28ekim.bundle main
```

Kişi 2 alır ve kendi dalına katar:

```bash
git switch main && git pull ../main_28ekim.bundle main && git switch kisi2 && git merge main
```

**Kurallar:**
- Commit'ler küçük ve anlamlı, mesajlar Türkçe. Her commit'ten önce o kısmın testleri geçmeli.
- Birleştirmeden sonra, API çalışırken üretilen dosyalar tek komutla yenilenir: `sh scripts/api_tipleri_yenile.sh` (`docs/openapi.json` + `web/src/api/schema.d.ts`).
- `.env`, parola, `_kaynak/` ve yarışma belgeleri depoya girmez (CON-006).
- Port çakışması varsa `.env` ile değiştirilir: `API_PORT=18000`, `WEB_PORT=18080`.
- Bu bilgisayarda (Kişi 1) Windows Uygulama Denetimi scikit-learn'ü Windows'ta engelliyor. Model eğitimi ve testleri Docker içinde (Linux) çalıştırılır.

## 6. İki kulvar arasındaki sözleşme (YZ entegrasyonu)

Kişi 2'nin sunucu tarafında dokunacağı yerler sınırlıdır. Bu sayede Görev 3 çalışmasıyla çakışmaz.

- **Model dosyaları:**
  - `ml/models/model_a.joblib`, `ml/models/model_b.joblib`.
  - `ml/models/metadata.json`: sürüm, eğitim tarihi, hata ölçümleri.
  - Eğitilmiş küçük dosyalar depoya girer (değerlendirici eğitmek zorunda kalmasın).
- **Sunucuda tahmin:** `app/services/ai.py`.
  - `forecast_production(session, order) -> AiForecast | None`: `production.create_order` sonunda **tek satırla** çağrılır.
  - `forecast_cutting(session, cutting) -> AiForecast | None`: `cutting.create_cutting` sonunda çağrılır; `cutting_outputs.predicted_qty`'yi doldurur.
  - İkisi de hata durumunda `None` döner ve günlüğe yazar; iş akışını **asla durdurmaz** (`architecture.md` §6).
- **API çıktısı:**
  - `OrderOut`'a `forecast` alanı eklenir: `{expected_qty, yield_main_pct, ekp, model_version}` ya da `null`. Kabulden sonra gerçek değerle sapma hesaplanır.
  - `CuttingOut` satırlarındaki `predicted_kg` zaten var; Model B onu doldurur.
- **Uçlar:** `POST /ai/production-forecast`, `POST /ai/cutting-forecast`, `GET /ai/evaluation` (`api.md` "Yapay zekâ" bölümü).
- **Kayıt:** `ai_forecasts` tablosu hazır (`model`, `model_version`, `target_type`, `target_id`, `features`, `prediction`). Tahmin sonradan değişmez (sızıntı yok).
- **Web:** `ForecastCard` bileşeni, emir ve parçalama ayrıntı sayfalarına birer satırla eklenir. Bu iki sayfa Kişi 1'in sahipliğindedir; eklemeden önce haber verilir.

## 7. "Bitti" tanımı

Bir iş ancak şunların hepsi olunca biter:

1. Kod ve testler yazıldı; o kısmın bütün testleri geçiyor (sunucu: `pytest`, `ruff`; web: `tsc`, `oxlint`, `vitest`; Android: `gradlew testDebugUnitTest`).
2. Çalışan sistemde elle denendi; bütünlük denetimi 8/8.
3. `reports/test_results.md`'ye sonuç, `CHANGELOG.md`'ye kısa kayıt, `development_plan.md`'de durum satırı yazıldı.
4. Gerekiyorsa `api.md` / `data_model.md` güncellendi.
5. Yerel commit atıldı (GitHub'a değil).

## 8. Takvim

| Gün | Kişi 1 — Caner | Kişi 2 — arkadaş | Akşam kontrolü |
|---|---|---|---|
| 27 Ekim Sal | T-16a izleme API, demo profili | Kurulum, testleri çalıştırma, T-18 başlangıç | Paket teslim edildi; arkadaşta testler yeşil |
| 28 Ekim Çar | T-16b geri çağırma, T-16c ikinci kademe | T-18 bitir, T-19 Model A | **Birleştirme 1** |
| 29 Ekim Per (tatil) | T-17 web ekranları, eksik hareketler | T-20 Model B, T-21 entegrasyon başlangıç | **Birleştirme 2** — M3: üç görev çalışıyor |
| 30 Ekim Cum | T-22 raporlar, FR-607 | T-21 bitir, YZ raporu, T-23 kabul testleri | **Birleştirme 3** — M4: kabul testleri yeşil |
| 31 Ekim Cmt | Belgeler (T-25), APK, hata düzeltme | T-26 temiz kurulum (kendi PC), video senaryosu | **Kod dondurma 20:00**, video çekimi — M5 |
| 1 Kasım Paz | GitHub'a gönderim (ön izleme + onay), depo herkese açık | Videoyu oturum kapalı tarayıcıda deneme | Kontrol listesi tam; **e-posta öğleden sonra** — M6 |

**Geride kalınırsa önce bunlar bırakılır** (`development_plan.md` §5): yeniden işleme hareketi, rapor süzgeçleri, web'de görsel cila. ★K gereksinimlerden (Görev 3, iki YZ modeli, demo senaryosu, video) hiçbiri kısılmaz.
