# Ekran Görüntüleri

Uygulamanın bütün ekranları, demo verisiyle (şartname senaryosu). Sistemi kurmadan uygulamayı görmek için.
Web görüntüleri 1440 px genişlikte tam sayfa; Android görüntüleri emülatörden (1080 × 2400).
27 Ekim 2026'da çalışan sistemden çekildi.

İçindekiler: [Web — giriş ve ana sayfa](#1) · [Web — ana veriler, alış, stok ve lotlar](#2) · [Web — Görev 1: dış üretim ve gerçek maliyet (EKP)](#3) · [Web — Görev 2: kuzu parçalama ve satış](#4) · [Web — Görev 3: izleme ve geri çağırma](#5) · [Web — raporlar ve yapay zekâ](#6) · [Web — telefon genişliği](#7) · [Android (Kotlin) — lot bazlı satış ve geri çağırma](#8)

<a id="1"></a>

## Web — giriş ve ana sayfa

**Yönetici girişi (`yonetici` / `yonetici123`, yalnız yerel demo parolası).**

<img src="web/01_giris.jpg" alt="Yönetici girişi (`yonetici` / `yonetici123`, yalnız yerel demo parolası).">

**Ana sayfa: 3D gösterge kutuları (son EKP 18,16 €, açık geri çağırma, uyarı, defter bütünlüğü 8/8), şartname senaryosu kısayolları.**

<img src="web/02_ana_sayfa.jpg" alt="Ana sayfa: 3D gösterge kutuları (son EKP 18,16 €, açık geri çağırma, uyarı, defter bütünlüğü 8/8), şartname senaryosu kısayolları.">

<a id="2"></a>

## Web — ana veriler, alış, stok ve lotlar

**Ürün kartları: hammadde, mamul, parça; birim, lot öneki, satış fiyatı, raf ömrü.**

<img src="web/03_urunler.jpg" alt="Ürün kartları: hammadde, mamul, parça; birim, lot öneki, satış fiyatı, raf ömrü.">

**Cariler: tedarikçiler, dış üretici, marketler ve şubeleri, iletişim bilgileriyle.**

<img src="web/04_cariler.jpg" alt="Cariler: tedarikçiler, dış üretici, marketler ve şubeleri, iletişim bilgileriyle.">

**Hammadde alışları: ET-2026-001, BAH-2026-014, BAG-2026-007, KUZU-2026-012.**

<img src="web/05_hammadde_alislari.jpg" alt="Hammadde alışları: ET-2026-001, BAH-2026-014, BAG-2026-007, KUZU-2026-012.">

**Yeni alış formu: lot, miktar, fiyat, fatura tutarı, ek maliyet kalemleri.**

<img src="web/06_yeni_hammadde_alisi.jpg" alt="Yeni alış formu: lot, miktar, fiyat, fatura tutarı, ek maliyet kalemleri.">

**Stok durumu: depo × lot bakiyeleri.**

<img src="web/07_stok_durumu.jpg" alt="Stok durumu: depo × lot bakiyeleri.">

**Lotlar: köken, durum (aktif/bloke), kalan miktar ve değer.**

<img src="web/08_lotlar.jpg" alt="Lotlar: köken, durum (aktif/bloke), kalan miktar ve değer.">

**Lot ayrıntısı: kaynak lotlar, hareket geçmişi (kim, ne zaman, hangi belge), bakiye = hareketlerin toplamı; fire/imha ve ters kayıt düğmeleri.**

<img src="web/09_lot_ayrintisi_SUC-2026-045.jpg" alt="Lot ayrıntısı: kaynak lotlar, hareket geçmişi (kim, ne zaman, hangi belge), bakiye = hareketlerin toplamı; fire/imha ve ters kayıt düğmeleri.">

**Depolar arası transfer (ör. araca yükleme).**

<img src="web/10_transferler.jpg" alt="Depolar arası transfer (ör. araca yükleme).">

<a id="3"></a>

## Web — Görev 1: dış üretim ve gerçek maliyet (EKP)

**Dış üretim emirleri.**

<img src="web/11_dis_uretim_emirleri.jpg" alt="Dış üretim emirleri.">

**URT-2026-045: taslak → sevk → teslim; girdiler; EKP dökümü 1.543,50 € / 85 = 18,16 €; kâr ve marj; yapay zekâ kartı (tahmin 84, gerçek 85, sapma +1).**

<img src="web/12_dis_uretim_emri_URT-2026-045.jpg" alt="URT-2026-045: taslak → sevk → teslim; girdiler; EKP dökümü 1.543,50 € / 85 = 18,16 €; kâr ve marj; yapay zekâ kartı (tahmin 84, gerçek 85, sapma +1).">

**Yeni dış üretim emri formu.**

<img src="web/13_yeni_dis_uretim_emri.jpg" alt="Yeni dış üretim emri formu.">

**Yeniden işleme: işletme içinde lotlardan yeni lot (ör. iade gelen ürünün yeniden paketlenmesi).**

<img src="web/14_yeniden_isleme.jpg" alt="Yeniden işleme: işletme içinde lotlardan yeni lot (ör. iade gelen ürünün yeniden paketlenmesi).">

<a id="4"></a>

## Web — Görev 2: kuzu parçalama ve satış

**Parçalamalar.**

<img src="web/15_parcalama_listesi.jpg" alt="Parçalamalar.">

**PRC-2026-012: alış maliyet kalemleri (287,50 € + 63,50 € = 351,00 €), ağırlık dengesi 25 = 22 + 3 fire, değer ağırlıklı dağıtım kuruşu kuruşuna 351,00 €; standart oran, yapay zekâ tahmini ve gerçek kg.**

<img src="web/16_parcalama_PRC-2026-012.jpg" alt="PRC-2026-012: alış maliyet kalemleri (287,50 € + 63,50 € = 351,00 €), ağırlık dengesi 25 = 22 + 3 fire, değer ağırlıklı dağıtım kuruşu kuruşuna 351,00 €; standart oran, yapay zekâ tahmini ve gerçek kg.">

**Yeni parçalama: reçete, giriş lotu, ağırlık.**

<img src="web/17_yeni_parcalama.jpg" alt="Yeni parçalama: reçete, giriş lotu, ağırlık.">

**Parçalama reçetesi: parçalar, standart oranlar, değer katsayıları, fire.**

<img src="web/18_parcalama_receteleri.jpg" alt="Parçalama reçetesi: parçalar, standart oranlar, değer katsayıları, fire.">

**Satışlar (Android'den gelen) ve müşteri iadeleri.**

<img src="web/19_satislar_ve_iadeler.jpg" alt="Satışlar (Android&#x27;den gelen) ve müşteri iadeleri.">

<a id="5"></a>

## Web — Görev 3: izleme ve geri çağırma

**İleri izleme ET-2026-001: 3D lot zinciri → SUC-2026-045 → Market A 30 / B 25 / C 30; bizdeki stok 0; iletişim, satış belgeleri, ikinci kademe (B'nin şubeleri kesin, A ve C sonrası bilinmiyor).**

<img src="web/20_izleme_ileri_ET-2026-001.jpg" alt="İleri izleme ET-2026-001: 3D lot zinciri → SUC-2026-045 → Market A 30 / B 25 / C 30; bizdeki stok 0; iletişim, satış belgeleri, ikinci kademe (B&#x27;nin şubeleri kesin, A ve C sonrası bilinmiyor).">

**Geri izleme SUC-2026-045: üç hammadde lotu, tedarikçileri ve alış belgeleri, URT-2026-045.**

<img src="web/21_izleme_geri_SUC-2026-045.jpg" alt="Geri izleme SUC-2026-045: üç hammadde lotu, tedarikçileri ve alış belgeleri, URT-2026-045.">

**Geri çağırma başlatma: neden yazılır; kaynak ve türevler tek işlemde bloke olur.**

<img src="web/24_geri_cagirma_baslatma_penceresi.jpg" alt="Geri çağırma başlatma: neden yazılır; kaynak ve türevler tek işlemde bloke olur.">

**Geri çağırma GC-2026-001: etkilenen zincir (kırmızı = bloke), market listesi, iletişim, CSV iletişim listesi, iade al, ikinci kademe ekle, kapat (imha/serbest).**

<img src="web/27_geri_cagirma_GC-2026-001.jpg" alt="Geri çağırma GC-2026-001: etkilenen zincir (kırmızı = bloke), market listesi, iletişim, CSV iletişim listesi, iade al, ikinci kademe ekle, kapat (imha/serbest).">

**Geri çağırmalar listesi.**

<img src="web/28_geri_cagirma_listesi.jpg" alt="Geri çağırmalar listesi.">

**Uyarı: geri çağrılmış lotun çevrimdışı satışı (Android) yöneticiye bildirildi; menüde okunmamış sayısı.**

<img src="web/29_uyarilar.jpg" alt="Uyarı: geri çağrılmış lotun çevrimdışı satışı (Android) yöneticiye bildirildi; menüde okunmamış sayısı.">

**Geri çağırmadan sonra izleme: lotlar bloke.**

<img src="web/30_izleme_geri_cagirma_sonrasi.jpg" alt="Geri çağırmadan sonra izleme: lotlar bloke.">

**Geri çağırmadan sonra ana sayfa: açık geri çağırma ve uyarı sayıları.**

<img src="web/38_ana_sayfa_geri_cagirma_sonrasi.jpg" alt="Geri çağırmadan sonra ana sayfa: açık geri çağırma ve uyarı sayıları.">

<a id="6"></a>

## Web — raporlar ve yapay zekâ

**Yedi rapor (her biri süzgeçli, CSV indirilebilir).**

<img src="web/23_raporlar.jpg" alt="Yedi rapor (her biri süzgeçli, CSV indirilebilir).">

**Alış raporu: fatura, ek maliyet, lot değeri.**

<img src="web/31_rapor_alis.jpg" alt="Alış raporu: fatura, ek maliyet, lot değeri.">

**Üretim raporu: miktar farkları, EKP, kâr/marj, yapay zekâ tahmini ve sapma.**

<img src="web/32_rapor_uretim.jpg" alt="Üretim raporu: miktar farkları, EKP, kâr/marj, yapay zekâ tahmini ve sapma.">

**Parçalama raporu: standart, yapay zekâ tahmini, gerçek kg ve fark; dağıtılan maliyet.**

<img src="web/33_rapor_parcalama.jpg" alt="Parçalama raporu: standart, yapay zekâ tahmini, gerçek kg ve fark; dağıtılan maliyet.">

**Lot hareketleri raporu: yürüyen bakiye (bakiye = hareketlerin toplamı).**

<img src="web/34_rapor_lot_hareketleri.jpg" alt="Lot hareketleri raporu: yürüyen bakiye (bakiye = hareketlerin toplamı).">

**Satış raporu: müşteri, lot, tutar, maliyet, brüt kâr, kanal, iade, ihlal.**

<img src="web/35_rapor_satis.jpg" alt="Satış raporu: müşteri, lot, tutar, maliyet, brüt kâr, kanal, iade, ihlal.">

**Geri çağırma raporu: etkilenen lotlar, alıcılar, müşteride kalan miktarlar.**

<img src="web/36_rapor_geri_cagirma.jpg" alt="Geri çağırma raporu: etkilenen lotlar, alıcılar, müşteride kalan miktarlar.">

**Bütünlük raporu: defter–özet kuralları I-1…I-8, hepsi tutarlı.**

<img src="web/37_rapor_butunluk.jpg" alt="Bütünlük raporu: defter–özet kuralları I-1…I-8, hepsi tutarlı.">

**Yapay zekâ: Model A ve B, referans yöntemle karşılaştırma (hata çubukları), örnek tahminler, sistemdeki gerçek kayıtlar, sınırlılıklar.**

<img src="web/22_yapay_zeka.jpg" alt="Yapay zekâ: Model A ve B, referans yöntemle karşılaştırma (hata çubukları), örnek tahminler, sistemdeki gerçek kayıtlar, sınırlılıklar.">

<a id="7"></a>

## Web — telefon genişliği

**Ana sayfa, 390 px genişlikte.**

<img src="web/25_telefon_ana_sayfa.jpg" alt="Ana sayfa, 390 px genişlikte." width="320">

**İzleme ekranı, 390 px genişlikte (şema yatay kayar).**

<img src="web/26_telefon_izleme.jpg" alt="İzleme ekranı, 390 px genişlikte (şema yatay kayar)." width="320">

<a id="8"></a>

## Android (Kotlin) — lot bazlı satış ve geri çağırma

**Giriş: sunucu adresi, satış kullanıcısı (`satis1` / `satis123`).**

<img src="android/A01_giris.png" alt="Giriş: sunucu adresi, satış kullanıcısı (`satis1` / `satis123`)." width="320">

**Ana sayfa: üst bant, gösterge kutuları (araçta lot, bloke lot, bekleyen satış), eşitleme.**

<img src="android/A02_ana_sayfa.png" alt="Ana sayfa: üst bant, gösterge kutuları (araçta lot, bloke lot, bekleyen satış), eşitleme." width="320">

**Araç deposu stoku (lot ve son kullanma tarihi).**

<img src="android/A03_ana_sayfa_stok_ve_satislar.png" alt="Araç deposu stoku (lot ve son kullanma tarihi)." width="320">

**Yeni satış: müşteri ve lot seçimi (ilk biten önce önerilir).**

<img src="android/A04_yeni_satis.png" alt="Yeni satış: müşteri ve lot seçimi (ilk biten önce önerilir)." width="320">

**Satır: 1,5 kg × 26,00 € = 39,00 €.**

<img src="android/A05_satis_satiri_eklendi.png" alt="Satır: 1,5 kg × 26,00 € = 39,00 €." width="320">

**Satış kaydedildi ve gönderildi.**

<img src="android/A06_satis_sonrasi_ana_sayfa.png" alt="Satış kaydedildi ve gönderildi." width="320">

**Son satışlar: "Gönderildi · SAT-2026-0104".**

<img src="android/A07_satis_gonderildi.png" alt="Son satışlar: &quot;Gönderildi · SAT-2026-0104&quot;." width="320">

**Uçak modunda satış: telefona kaydedildi, "gönderilmeyi bekliyor"; kullanılabilir miktar bekleyen satış kadar düşük.**

<img src="android/A08_cevrimdisi_satis_bekliyor.png" alt="Uçak modunda satış: telefona kaydedildi, &quot;gönderilmeyi bekliyor&quot;; kullanılabilir miktar bekleyen satış kadar düşük." width="320">

**Bağlantı gelince eşitleme: geri çağrılan lotlar "Bloke lot 2".**

<img src="android/A09_eslestirme_sonrasi_bloke_lotlar.png" alt="Bağlantı gelince eşitleme: geri çağrılan lotlar &quot;Bloke lot 2&quot;." width="320">

**Bloke lotlar kırmızı: "BLOKE — satılamaz", ne yapılacağı yazılı.**

<img src="android/A10_bloke_lotlar_ve_uyari.png" alt="Bloke lotlar kırmızı: &quot;BLOKE — satılamaz&quot;, ne yapılacağı yazılı." width="320">

**Çevrimdışı yapılan satış sunucuda kaydedildi, uyarı döndü: geri çağrılmış lot satıldı, ihlal yöneticiye bildirildi.**

<img src="android/A11_cevrimdisi_satis_uyarisi.png" alt="Çevrimdışı yapılan satış sunucuda kaydedildi, uyarı döndü: geri çağrılmış lot satıldı, ihlal yöneticiye bildirildi." width="320">

**Satış ekranında bloke lot seçilemez: "Geri çağrıldı: bu lot hiçbir kanaldan satılamaz".**

<img src="android/A12_satis_ekraninda_bloke_lot.png" alt="Satış ekranında bloke lot seçilemez: &quot;Geri çağrıldı: bu lot hiçbir kanaldan satılamaz&quot;." width="320">
