# Kabul Testleri Raporu (T-23)

| | |
|---|---|
| Tarih | 27 Ekim 2026 |
| Kapsam | Şartname kabul testleri AT-01…AT-15 (`docs/testing_strategy.md` §3) ve yedi rapor |
| Kod | `tests/test_kabul.py`, `tests/conftest.py` |
| Çalıştırma | `sh scripts/kabul_testleri.sh` (depo kökünden) |
| Sonuç | **23 / 23 geçti** · ET-2026-001 ileri izlemesi **0,043 sn** (NFR-009: < 2 sn) |

## Nasıl çalışır

Sunucu birim testlerinden (`backend/tests`, 170 test) farkı şudur: kabul testleri **çalışan sisteme gerçek HTTP istekleriyle** bağlanır. Veritabanı geri alınmaz. Sistem, değerlendiricinin kuracağı hâliyle sınanır.

1. Betik sistemi **ayrı bir kopyada sıfırdan** kurar (`docker compose -p avatar-kabul up --build`, varsayılan demo profili). Böylece AT-14 (temiz kurulum) her çalıştırmada kendiliğinden sınanır. Geliştirme veritabanına ve açık sisteme dokunulmaz.
2. Testler API konteynerinin içinden ağ üzerinden koşar. Yalnız Python'un standart kütüphanesi kullanılır.
3. Sıra bilinçlidir:
   - önce yalnız okuyan ve kendi yeni lotlarıyla çalışan testler (Görev 1–2),
   - sonra demo senaryosunu okuyan testler (izleme, ikinci kademe),
   - en son demo verisini değiştiren testler (geri çağırma).
4. Kopya iş bitince silinir. İncelemek için betik `KOPYAYI_BIRAK=1` ile çalıştırılabilir.

## Sonuçlar

| Kabul testi | Ne sınandı (şartname rakamlarıyla) | Sonuç |
|---|---|---|
| AT-14 Temiz kurulum | Sıfırdan kurulumda sağlık denetimi `ok`; SUC-2026-045 85 paket, 1.543,50 €; URT-2026-045 kayıtlı | Geçti |
| AT-01 Dış üretim EKP | Yeni lotlarla alış → emir → sevk → kabul, gerçek HTTP ile: toplam 1.543,50 €, EKP 18,16 € (saklanan ≥ 18,1588), lot değeri 1.543,50 €; demo emri de aynı | Geçti |
| AT-02 Kâr ve marj | VKP 24,90 € → birim brüt kâr 6,74 €, marj %27,07 | Geçti |
| AT-15 Miktar farkları | Plan 87, teslim 85 (fark −2); baharat 1,5 kg tüketildi, 0,5 kg iade; EKP 85'e göre 18,02 €; fark üretim raporunda da görünüyor | Geçti |
| AT-03 Maliyet dağıtımı | 25 kg kuzu, 287,50 € + 63,50 € ek maliyet = 351,00 €. Miktara göre 111,68 / 63,82 / 79,77 / 47,87 / 47,86; değere göre 123,41 / 83,34 / 72,12 / 33,66 / 38,47; ikisinde de toplam 351,00 € | Geçti |
| AT-04 Ağırlık dengesi | Fire tartılmadan onay → `VALIDATION_ERROR`; fire 0 → `WEIGHT_IMBALANCE` (fark 3 kg); fire 3 kg → onaylandı | Geçti |
| AT-05 Fatura farkı | 25 × 11,50 = 287,50 € iken fatura 351,00 €: açıklamasız → `AMOUNT_MISMATCH_NOTE_REQUIRED`; açıklamayla kabul | Geçti |
| AT-06 İleri izleme | ET-2026-001 → SUC-2026-045; Market A 30, B 25, C 30; bizdeki stok 0; iletişim ve satış belgesi (SAT-2026-0101); süre 0,043 sn | Geçti |
| AT-07 Geri izleme | SUC-2026-045 → ET-2026-001, BAH-2026-014, BAG-2026-007 ve tedarikçileri; URT-2026-045 | Geçti |
| AT-09 İkinci kademe | Market B: kesin (Şube 1: 15, Şube 2: 10); Market A ve C: bilinen son alıcı, sonrası bilinmiyor | Geçti |
| AT-11 Tekrar güvenli gönderim | Aynı satış iki kez gönderildi: `ACCEPTED` + `DUPLICATE`, aynı belge no, tek satış | Geçti |
| AT-08 Geri çağırma | ET-2026-001 ve SUC-2026-045 bloke; liste A 30 / B 25 / C 30; CSV'de marketler ve şubeler; iade alınan bloke lot araca transfer edilemiyor ve üretimde kullanılamıyor (`LOT_BLOCKED`) | Geçti |
| AT-12 Çevrimdışı ihlal | KUZU-2026-012 geri çağrıldı → cihaz eşitlemede parça lotunu `BLOKE` görüyor; eşitlemeden yapılmış satış `ACCEPTED_WITH_WARNING`; müşteri listede ihlal işaretli; uyarı düştü | Geçti |
| AT-10 Defter | Eksi stoka düşüren transfer `INSUFFICIENT_STOCK`; fire ve ters kaydı (hareket silinmeden); bütünlük raporu 8/8 | Geçti |
| AT-13 Yapay zekâ | Model A paket ve EKP hatası, Model B kg hatası referanstan düşük; sınırlılıklar yazılı; testte açılan emrin tahmini canlı kaydedildi | Geçti |
| Raporlar (FR-601…607) | Yedi rapor demo verisiyle dolu ve CSV iniyor | 7 / 7 geçti |

## Çalıştırma çıktısı (27 Ekim 2026)

```
1/3 Sistem sıfırdan kuruluyor (proje: avatar-kabul, API portu 18200)…
2/3 Kabul testleri çalışıyor…
Sistem: http://api:8000/api/v1 · ET-2026-001 ileri izleme süresi: 0.043 sn
23 passed in 15.21s
3/3 Kopya siliniyor…
```

## Sınırlar

- **Android arayüzü** bu testlerde HTTP düzeyinde sınanır (eşitleme uçları, `satis1` kullanıcısı). Uygulamanın ekranları emülatörde elle denendi (`reports/test_results.md`). Kurallar Android birim testleriyle (17) denetlenir.
- **Web arayüzü** bu testlerde yok. Ekranlar tarayıcıda elle denendi, birim testleri (16) ayrıca çalışır.
- **AT-14'ün asıl hâli** temiz bir bilgisayarda yalnız README ile kurulumdur (T-26). Bu betik aynı bilgisayarda ama sıfırdan kurulmuş ayrı bir kopyada çalışır.
