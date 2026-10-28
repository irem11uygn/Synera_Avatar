# Ekran Görüntüleri

Uygulamanın bütün ekranları, demo verisiyle (şartname senaryosu ve örnek günlük işler). Sistemi kurmadan uygulamayı görmek için.
Web görüntüleri 1440 px genişlikte tam sayfa; Android görüntüleri emülatörden (yarı boyut).
Web görüntüleri 28 Ekim 2026'da, sıfırdan kurulan sistemden turkuaz + 3B arayüzle çekildi (alarm, denetim, e-posta, panel ve hesaplayıcı ekranları dahil). Android görüntüleri aynı günün ilk turundan; telefondaki üst çubuk artık turkuazdır.

İçindekiler: [Web — giriş ve rollere göre ana sayfa](#1) · [Web — satış, gün sonu](#2) · [Web — depo: mal kabul, stok, son kullanma, sayım](#3) · [Web — üretim: fason üretim (Görev 1), parçalama (Görev 2)](#4) · [Web — kalite: izleme, tatbikat, geri çağırma (Görev 3)](#5) · [Web — raporlar, yapay zekâ, yönetim](#6) · [Web — alarm, denetim, e-posta, hesaplayıcılar, faturadan doldur](#7) · [Web — yazdırılabilir belgeler](#8) · [Web — İngilizce ve telefon genişliği](#9) · [Android (Kotlin) — araçtan satış](#10)

<a id="1"></a>

## Web — giriş ve rollere göre ana sayfa

**Giriş. Sağ üstte dil seçimi (TR / EN). Demo kullanıcıları README'de; şifreler yalnız yerel demo içindir.**

<img src="web/01_giris.jpg" alt="Giriş. Sağ üstte dil seçimi (TR / EN). Demo kullanıcıları README&#x27;de; şifreler yalnız yerel demo içindir.">

**Mağaza çalışanının ana sayfası (`magaza1`): bugün yapılacaklar, hızlı işlemler (mağaza satışı, iade al, gün sonu), bugünkü satış. Menüde yalnız kendi işinin ekranları.**

<img src="web/02_ana_sayfa_magaza.jpg" alt="Mağaza çalışanının ana sayfası (`magaza1`): bugün yapılacaklar, hızlı işlemler (mağaza satışı, iade al, gün sonu), bugünkü satış. Menüde yalnız kendi işinin ekranları.">

**Depo sorumlusunun ana sayfası (`depo1`): dolmak üzere lotlar, azalan stok; mal kabul, araca yükleme, sayım.**

<img src="web/03_ana_sayfa_depo.jpg" alt="Depo sorumlusunun ana sayfası (`depo1`): dolmak üzere lotlar, azalan stok; mal kabul, araca yükleme, sayım.">

**Yöneticinin ana sayfası (turkuaz + 3B görünüm): bugün yapılacaklar, özet ve panel — EKP gerçek/model tahmini (kesikli), hedef/gerçekleşen göstergesi, maliyet halkası (1.543,50 € → 18,16 €), izometrik 3B parça maliyetleri, müşteri sevkiyatı, açık alarmlar. Her grafikte "Tablo" görünümü var.**

<img src="web/04_ana_sayfa_yonetici.jpg" alt="Yöneticinin ana sayfası (turkuaz + 3B görünüm): bugün yapılacaklar, özet ve panel — EKP gerçek/model tahmini (kesikli), hedef/gerçekleşen göstergesi, maliyet halkası (1.543,50 € → 18,16 €), izometrik 3B parça maliyetleri, müşteri sevkiyatı, açık alarmlar. Her grafikte &quot;Tablo&quot; görünümü var.">

<a id="2"></a>

## Web — satış, gün sonu

**Mağaza satışı üç adım: müşteri, ürünler, ödeme türü. Lot elle seçilmez; son kullanma tarihi en yakın satılabilir lot kendiliğinden seçilir.**

<img src="web/05_magaza_satisi.jpg" alt="Mağaza satışı üç adım: müşteri, ürünler, ödeme türü. Lot elle seçilmez; son kullanma tarihi en yakın satılabilir lot kendiliğinden seçilir.">

**Satışlar ve iadeler: güne göre süzme, mağaza ve araç satışları, ödeme türü, fiş yazdırma; satır açılınca iade alma.**

<img src="web/06_satislar_ve_iadeler.jpg" alt="Satışlar ve iadeler: güne göre süzme, mağaza ve araç satışları, ödeme türü, fiş yazdırma; satır açılınca iade alma.">

**Gün sonu: satış, iade, net; ödeme türüne ve satıcıya göre toplamlar, kasadaki nakit; yöneticiye brüt kâr.**

<img src="web/07_gun_sonu.jpg" alt="Gün sonu: satış, iade, net; ödeme türüne ve satıcıya göre toplamlar, kasadaki nakit; yöneticiye brüt kâr.">

<a id="3"></a>

## Web — depo: mal kabul, stok, son kullanma, sayım

**Mal kabul: tedarikçiden gelen her teslimat bir lot numarası alır; ek masraflar maliyete eklenir.**

<img src="web/08_mal_kabul.jpg" alt="Mal kabul: tedarikçiden gelen her teslimat bir lot numarası alır; ek masraflar maliyete eklenir.">

**Yeni mal kabul formu: lot, miktar, fiyat, fatura tutarı, ek maliyet.**

<img src="web/09_yeni_mal_kabul.jpg" alt="Yeni mal kabul formu: lot, miktar, fiyat, fatura tutarı, ek maliyet.">

**Stok durumu: depo, lot, son kullanma, durum; lot ya da ürün bazında.**

<img src="web/10_stok_durumu.jpg" alt="Stok durumu: depo, lot, son kullanma, durum; lot ya da ürün bazında.">

**Son kullanma takibi: süresi geçen ve yaklaşan mal; tek tıkla imha kaydı ve etiket yazdırma.**

<img src="web/11_son_kullanma_takibi.jpg" alt="Son kullanma takibi: süresi geçen ve yaklaşan mal; tek tıkla imha kaydı ve etiket yazdırma.">

**Sayım: rafta sayılan miktar yazılır (isteğe bağlı kör sayım); eksik fire olarak düşülür, fazla raporlanır. Önceki sayımlar ve tutanak.**

<img src="web/12_sayim.jpg" alt="Sayım: rafta sayılan miktar yazılır (isteğe bağlı kör sayım); eksik fire olarak düşülür, fazla raporlanır. Önceki sayımlar ve tutanak.">

**Araca yükleme ve depolar arası aktarma.**

<img src="web/13_araca_yukleme.jpg" alt="Araca yükleme ve depolar arası aktarma.">

**Lotlar (partiler): köken, durum, kalan miktar ve değer.**

<img src="web/14_lotlar.jpg" alt="Lotlar (partiler): köken, durum, kalan miktar ve değer.">

**Lot kartı SUC-2026-045: kaynak lotlar, depo bakiyeleri, bütün hareketler; ileri/geri izleme, fire/imha, geri alma.**

<img src="web/15_lot_karti_SUC-2026-045.jpg" alt="Lot kartı SUC-2026-045: kaynak lotlar, depo bakiyeleri, bütün hareketler; ileri/geri izleme, fire/imha, geri alma.">

<a id="4"></a>

## Web — üretim: fason üretim (Görev 1), parçalama (Görev 2)

**Fason üretim emirleri: emir aç → hammaddeyi sevk et → ürünü teslim al.**

<img src="web/16_fason_uretim.jpg" alt="Fason üretim emirleri: emir aç → hammaddeyi sevk et → ürünü teslim al.">

**URT-2026-045: girdiler, birim maliyet (EKP) dökümü 1.543,50 € / 85 = 18,16 €, kâr ve marj, yapay zekâ tahmini ile gerçek.**

<img src="web/17_fason_uretim_emri_URT-2026-045.jpg" alt="URT-2026-045: girdiler, birim maliyet (EKP) dökümü 1.543,50 € / 85 = 18,16 €, kâr ve marj, yapay zekâ tahmini ile gerçek.">

**Parçalamalar.**

<img src="web/18_parcalama.jpg" alt="Parçalamalar.">

**PRC-2026-012: alış maliyeti 351,00 €, ağırlık dengesi 25 = 22 + 3 fire, piyasa değerine göre kuruşu kuruşuna dağıtım; standart oran, YZ tahmini ve gerçek kg.**

<img src="web/19_parcalama_PRC-2026-012.jpg" alt="PRC-2026-012: alış maliyeti 351,00 €, ağırlık dengesi 25 = 22 + 3 fire, piyasa değerine göre kuruşu kuruşuna dağıtım; standart oran, YZ tahmini ve gerçek kg.">

**Parçalama reçetesi: parçalar, standart oranlar, değer katsayıları.**

<img src="web/20_parcalama_receteleri.jpg" alt="Parçalama reçetesi: parçalar, standart oranlar, değer katsayıları.">

**Yeniden işleme: elimizdeki lotlardan yeni ürün; yeni lot kullanılanlara bağlanır.**

<img src="web/21_yeniden_isleme.jpg" alt="Yeniden işleme: elimizdeki lotlardan yeni ürün; yeni lot kullanılanlara bağlanır.">

<a id="5"></a>

## Web — kalite: izleme, tatbikat, geri çağırma (Görev 3)

**İleri izleme ET-2026-001 → SUC-2026-045 → Market A 30 / B 25 / C 30; iletişim bilgileri, müşterinin dağıttığı yerler.**

<img src="web/22_izleme_ileri_ET-2026-001.jpg" alt="İleri izleme ET-2026-001 → SUC-2026-045 → Market A 30 / B 25 / C 30; iletişim bilgileri, müşterinin dağıttığı yerler.">

**Geri izleme SUC-2026-045: hammadde lotları, tedarikçiler, URT-2026-045.**

<img src="web/23_izleme_geri_SUC-2026-045.jpg" alt="Geri izleme SUC-2026-045: hammadde lotları, tedarikçiler, URT-2026-045.">

**Geri çağırma tatbikatı (denetimlerde istenir): tedarikçiler, elimizdeki stok, aranacak müşteriler ve bulma süresi; hiçbir lot kapatılmaz.**

<img src="web/24_geri_cagirma_tatbikati.jpg" alt="Geri çağırma tatbikatı (denetimlerde istenir): tedarikçiler, elimizdeki stok, aranacak müşteriler ve bulma süresi; hiçbir lot kapatılmaz.">

**Kalite sorumlusunun ana sayfası, geri çağırma başlatıldıktan sonra.**

<img src="web/32_ana_sayfa_kalite_geri_cagirma_sonrasi.jpg" alt="Kalite sorumlusunun ana sayfası, geri çağırma başlatıldıktan sonra.">

**Geri çağırmalar listesi.**

<img src="web/33_geri_cagirmalar.jpg" alt="Geri çağırmalar listesi.">

**Geri çağırma: lot ve ondan yapılan bütün lotlar satışa kapalı; etkilenen zincir, aranacak müşteriler, iletişim listesi (CSV), bildirim yazdırma, iade alma, kapatma.**

<img src="web/34_geri_cagirma_ayrintisi.jpg" alt="Geri çağırma: lot ve ondan yapılan bütün lotlar satışa kapalı; etkilenen zincir, aranacak müşteriler, iletişim listesi (CSV), bildirim yazdırma, iade alma, kapatma.">

**Alarm merkezi (kalite sorumlusu): geri çağırma başladı (kritik), alış fiyatı artışı (uyarı), bloke lotta stok; okundu işaretleme. Hatalı giriş alarmı yalnız yöneticiye görünür.**

<img src="web/35_alarm_merkezi.jpg" alt="Alarm merkezi (kalite sorumlusu): geri çağırma başladı (kritik), alış fiyatı artışı (uyarı), bloke lotta stok; okundu işaretleme. Hatalı giriş alarmı yalnız yöneticiye görünür.">

<a id="6"></a>

## Web — raporlar, yapay zekâ, yönetim

**Raporlar: alış, üretim, parçalama, stok hareketi, satış, geri çağırma, bütünlük; CSV.**

<img src="web/25_raporlar.jpg" alt="Raporlar: alış, üretim, parçalama, stok hareketi, satış, geri çağırma, bütünlük; CSV.">

**Üretim raporu.**

<img src="web/26_rapor_uretim.jpg" alt="Üretim raporu.">

**Yapay zekâ tahminleri: iki model, referans yönteme göre hata, sistemdeki gerçek kayıtlar.**

<img src="web/27_yapay_zeka.jpg" alt="Yapay zekâ tahminleri: iki model, referans yönteme göre hata, sistemdeki gerçek kayıtlar.">

**Kullanıcılar (yalnız yönetici): rol ve araç ataması, pasifleştirme, geçici şifre.**

<img src="web/28_kullanicilar.jpg" alt="Kullanıcılar (yalnız yönetici): rol ve araç ataması, pasifleştirme, geçici şifre.">

**Ürünler ve fiyatlar: satış fiyatı, raf ömrü, kritik stok.**

<img src="web/29_urunler_ve_fiyatlar.jpg" alt="Ürünler ve fiyatlar: satış fiyatı, raf ömrü, kritik stok.">

**Müşteri ve tedarikçiler: iletişim bilgileri, şubeler, fasoncu.**

<img src="web/30_musteri_ve_tedarikciler.jpg" alt="Müşteri ve tedarikçiler: iletişim bilgileri, şubeler, fasoncu.">

**Şifremi değiştir (ilk girişte zorunlu ekranın aynısı).**

<img src="web/31_sifre_degistir.jpg" alt="Şifremi değiştir (ilk girişte zorunlu ekranın aynısı).">

<a id="7"></a>

## Web — alarm, denetim, e-posta, hesaplayıcılar, faturadan doldur

**Üst çubuktaki alarm zili: açık alarm sayısı (kritik varsa kırmızı) ve son beş alarm; yeni alarm gelince köşede bildirim açılır.**

<img src="web/45_alarm_zili.jpg" alt="Üst çubuktaki alarm zili: açık alarm sayısı (kritik varsa kırmızı) ve son beş alarm; yeni alarm gelince köşede bildirim açılır.">

**Denetim günlüğü (yönetici): kim, ne zaman, ne yaptı; önem, arama, kullanıcı ve tarih süzgeci, CSV. Hatalı girişler de burada.**

<img src="web/46_denetim_gunlugu.jpg" alt="Denetim günlüğü (yönetici): kim, ne zaman, ne yaptı; önem, arama, kullanıcı ve tarih süzgeci, CSV. Hatalı girişler de burada.">

**Rapor gönder (e-posta): rapor seç, alıcı ve not ekle, ön izlemede metnin tamamını gör; giden kutusu ve durumları (SMTP tanımlı değilse "Kuyrukta").**

<img src="web/47_rapor_gonder_eposta.jpg" alt="Rapor gönder (e-posta): rapor seç, alıcı ve not ekle, ön izlemede metnin tamamını gör; giden kutusu ve durumları (SMTP tanımlı değilse &quot;Kuyrukta&quot;).">

**Alarm ve e-posta ayarları: verim z-skoru, fiyat artışı ve hatalı giriş eşikleri; kuralları şimdi çalıştır; e-posta sunucusu durumu; kuralların listesi.**

<img src="web/48_alarm_ve_eposta_ayarlari.jpg" alt="Alarm ve e-posta ayarları: verim z-skoru, fiyat artışı ve hatalı giriş eşikleri; kuralları şimdi çalıştır; e-posta sunucusu durumu; kuralların listesi.">

**Ne olur hesaplayıcısı — EKP: hammadde, hizmet ücreti, teslim adedi; gerçek kayıtla aynı hesap (18,16 €).**

<img src="web/49_hesaplayici_ekp.jpg" alt="Ne olur hesaplayıcısı — EKP: hammadde, hizmet ücreti, teslim adedi; gerçek kayıtla aynı hesap (18,16 €).">

**Ne olur hesaplayıcısı — parçalama: değere ya da kiloya göre dağıtım, fire, ağırlık dengesi, 3B parça maliyeti.**

<img src="web/50_hesaplayici_parcalama.jpg" alt="Ne olur hesaplayıcısı — parçalama: değere ya da kiloya göre dağıtım, fire, ağırlık dengesi, 3B parça maliyeti.">

**Mal kabulde "Faturadan doldur": fatura/irsaliye metninden tedarikçi, belge no, tarih, ürün, miktar, lot, fiyat ve SKT önerisi. Kaydetmez; kullanıcı forma aktarıp kontrol eder.**

<img src="web/51_faturadan_doldur.jpg" alt="Mal kabulde &quot;Faturadan doldur&quot;: fatura/irsaliye metninden tedarikçi, belge no, tarih, ürün, miktar, lot, fiyat ve SKT önerisi. Kaydetmez; kullanıcı forma aktarıp kontrol eder.">

<a id="8"></a>

## Web — yazdırılabilir belgeler

**Lot etiketi: ürün, üretim ve son tüketim tarihi, Code 128 barkod (el terminaliyle okunur).**

<img src="web/40_yazdir_lot_etiketi.jpg" alt="Lot etiketi: ürün, üretim ve son tüketim tarihi, Code 128 barkod (el terminaliyle okunur).">

**Satış fişi / sevk irsaliyesi: ürün, lot, miktar, fiyat, ödeme; imza alanları.**

<img src="web/41_yazdir_fis_irsaliye.jpg" alt="Satış fişi / sevk irsaliyesi: ürün, lot, miktar, fiyat, ödeme; imza alanları.">

**Gün sonu raporu: ödeme türüne göre toplamlar ve sayılan kasa alanı.**

<img src="web/42_yazdir_gun_sonu.jpg" alt="Gün sonu raporu: ödeme türüne göre toplamlar ve sayılan kasa alanı.">

**Sayım tutanağı: sistemde, sayılan, fark, eksik maliyeti.**

<img src="web/43_yazdir_sayim_tutanagi.jpg" alt="Sayım tutanağı: sistemde, sayılan, fark, eksik maliyeti.">

**Müşteri başına geri çağırma bildirimi: ürün, lot, teslim belgesi, müşteride olması gereken miktar.**

<img src="web/44_yazdir_geri_cagirma_bildirimi.jpg" alt="Müşteri başına geri çağırma bildirimi: ürün, lot, teslim belgesi, müşteride olması gereken miktar.">

<a id="9"></a>

## Web — İngilizce ve telefon genişliği

**English: aynı ekranlar İngilizce; sayı ve tarih biçimi de dile göre.**

<img src="web/36_ingilizce_ana_sayfa.jpg" alt="English: aynı ekranlar İngilizce; sayı ve tarih biçimi de dile göre.">

**English: mağaza satışı (shop sale).**

<img src="web/37_ingilizce_magaza_satisi.jpg" alt="English: mağaza satışı (shop sale).">

**Telefon genişliğinde ana sayfa: menü sol üstten açılır.**

<img src="web/38_telefon_ana_sayfa.jpg" alt="Telefon genişliğinde ana sayfa: menü sol üstten açılır." width="320">

**Telefon genişliğinde mağaza satışı.**

<img src="web/39_telefon_magaza_satisi.jpg" alt="Telefon genişliğinde mağaza satışı." width="320">

**Telefon genişliğinde yöneticinin ana sayfası ve paneli: grafikler tek sütunda.**

<img src="web/52_telefon_yonetici_paneli.jpg" alt="Telefon genişliğinde yöneticinin ana sayfası ve paneli: grafikler tek sütunda." width="320">

<a id="10"></a>

## Android (Kotlin) — araçtan satış

**Giriş; dil seçimi (English / Türkçe).**

<img src="android/A01_giris.png" alt="Giriş; dil seçimi (English / Türkçe)." width="320">

**Ana ekran: eşitleme durumu, büyük "Yeni satış" düğmesi, bugünkü satış ve nakit. Alt menü: Satış, Stok, Geçmiş, Gün sonu.**

<img src="android/A02_ana_sayfa.png" alt="Ana ekran: eşitleme durumu, büyük &quot;Yeni satış&quot; düğmesi, bugünkü satış ve nakit. Alt menü: Satış, Stok, Geçmiş, Gün sonu." width="320">

**Araç stoku: son kullanma tarihi en yakın üstte; satışa kapalı ve süresi yaklaşan lotlar etiketli.**

<img src="android/A03_stok.png" alt="Araç stoku: son kullanma tarihi en yakın üstte; satışa kapalı ve süresi yaklaşan lotlar etiketli." width="320">

**Satış 1/4: müşteri ara ve seç.**

<img src="android/A04_satis_1_musteri.png" alt="Satış 1/4: müşteri ara ve seç." width="320">

**Satış 2/4: araçtaki satılabilir ürünler (geri çağrılan ve süresi geçen lot listede yok).**

<img src="android/A05_satis_2_urunler.png" alt="Satış 2/4: araçtaki satılabilir ürünler (geri çağrılan ve süresi geçen lot listede yok)." width="320">

**Sepet: 1,5 kg; lot kendiliğinden seçildi (SIRT-PRC-2026-012).**

<img src="android/A06_satis_sepet.png" alt="Sepet: 1,5 kg; lot kendiliğinden seçildi (SIRT-PRC-2026-012)." width="320">

**Satış 3/4: ödeme türü (nakit, kredi kartı, havale, veresiye).**

<img src="android/A07_satis_odeme.png" alt="Satış 3/4: ödeme türü (nakit, kredi kartı, havale, veresiye)." width="320">

**Satış 4/4: özet; satış önce telefona kaydedilir, bağlantı gelince gönderilir.**

<img src="android/A08_satis_ozet.png" alt="Satış 4/4: özet; satış önce telefona kaydedilir, bağlantı gelince gönderilir." width="320">

**Satıştan sonra ana ekran: bugünkü satış.**

<img src="android/A09_satis_sonrasi_ana_sayfa.png" alt="Satıştan sonra ana ekran: bugünkü satış." width="320">

**Geçmiş: satış sunucuya gönderildi (SAT numarası), ödeme türü.**

<img src="android/A10_gecmis.png" alt="Geçmiş: satış sunucuya gönderildi (SAT numarası), ödeme türü." width="320">

**Gün sonu (sunucudan): satış, iade, net; ödeme türüne göre; araçta kalan mal.**

<img src="android/A11_gun_sonu.png" alt="Gün sonu (sunucudan): satış, iade, net; ödeme türüne göre; araçta kalan mal." width="320">

**Araç sayımı: sayılan miktar yazılır, eksik fire olarak düşülür.**

<img src="android/A12_arac_sayimi.png" alt="Araç sayımı: sayılan miktar yazılır, eksik fire olarak düşülür." width="320">

**English: ana ekran.**

<img src="android/A13_ingilizce_ana_sayfa.png" alt="English: ana ekran." width="320">

**English: gün sonu (sayı 83.00, tarih 01/11/2026).**

<img src="android/A14_ingilizce_gun_sonu.png" alt="English: gün sonu (sayı 83.00, tarih 01/11/2026)." width="320">
