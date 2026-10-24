# Gereksinimler

| | |
|---|---|
| Sürüm | v0.1 (taslak — §7'deki sorular cevaplanınca kesinleşir) |
| Tarih | 24 Ekim 2026 |
| Kaynak | `_kaynak/AVATAR_Assessment.pdf` (Ş = şartname, § = bölüm), `_kaynak/yarisma_eposta.md` (E = e-postalar; E1–E3 tek tek) |
| Gerekçeler ve açıklamalar | `project_analysis.md` §3 |

**Öncelik:**
**★K** = zorunlu ve değerlendirme odağında (başarı için kritik) ·
**Z** = zorunlu ·
**Ö** = önerilen (şartnamede yok, kaliteyi artırmak için biz ekledik) ·
**İ** = isteğe bağlı (bonus).

**Kaynak türü:** *Belge* (açıkça yazıyor) veya *Çıkarım* (belgeden mantıkla çıkardık; gerekçesi analiz belgesinde).

**Sütunlar hakkında:** "Nasıl gerçekleştirileceği" sütunu mimari tasarımda (Aşama 5) eklenecek. Her gereksinimin hangi testle doğrulandığı `testing_strategy.md` içindeki izleme tablosundadır; burada yalnızca **tamamlanma ölçütü** yazılıdır.

---

## A. İşlevsel gereksinimler

### FR-1xx — Görev 1: Dış hizmetle üretim ve gerçek maliyet

| Kimlik | Gereksinim | Kaynak | Önc. | Tamamlanma ölçütü | İlişki |
|---|---|---|---|---|---|
| FR-101 | Hammadde kartları yönetilir: kod, ad, ölçü birimi, varsayılan alış fiyatı. | Ş§1 — Belge | Z | Kart oluşturulur, listelenir, güncellenir. | FR-102 |
| FR-102 | Hammadde girişi (alış) kaydedilir: tedarikçi, lot no, tarih, miktar, birim fiyat, uygunsa SKT. Giriş, lotu oluşturur ve stok giriş hareketi yazar. Lot no zorunludur. | Ş§1, Ş§3 — Belge | ★K | Lotsuz giriş reddedilir; giriş sonrası lot stoku = girilen miktar. | FR-301, NFR-002 |
| FR-103 | Ölçü birimleri (kg, adet/paket) ve ürün bazında dönüşüm tanımlanır (Narin Sucuk: 1 paket = 1 kg). | Ş§1 — Belge | Z | Paket ve kg cinsinden stok tutarlı gösterilir. | FR-110 |
| FR-104 | Stok, ürün / lot / depo kırılımında görüntülenir. | Ş§1 — Belge | Z | Ekran ve API'deki stok, hareketlerin toplamına eşit. | NFR-004 |
| FR-105 | Dış üretim emri oluşturulur: dış üretici, mamul, planlanan miktar, kullanılacak hammaddeler; durum akışıyla (taslak → sevk edildi → teslim alındı → kapandı). | Ş§1 — Belge | ★K | URT-2026-045 senaryosu baştan sona kaydedilebilir. | FR-106–110 |
| FR-106 | Hammadde sevki, seçilen lotlardan "dış üretici deposu"na **depo transferi** olarak kaydedilir (satış değil). | Ş§1 — Belge + Çıkarım | ★K | Sevk sonrası lot stoku ana depoda azalır, dış üretici deposunda artar; toplam değişmez. | FR-303 |
| FR-107 | Hizmet maliyeti (hizmet faturası: adet × birim ücret veya tutar) emre bağlanır; hammadde bedeli içermez. | Ş§1 — Belge | ★K | 85 × 5,50 € = 467,50 € emre maliyet olarak eklenir. | FR-110 |
| FR-108 | Mamul kabulü: teslim alınan miktar, yeni mamul lotu (ör. SUC-2026-045), tüketilen hammadde lotlarıyla miktarlı lot bağlantısı. | Ş§1, Ş§3 — Belge | ★K | Kabul sonrası SUC-2026-045 = 85 paket; ET-2026-001 vb. ile miktarlı bağlantı kayıtlı. | FR-302 |
| FR-109 | Miktar farkları kaydedilir: planlanan ↔ teslim alınan mamul; sevk edilen ↔ tüketilen hammadde; üreticiden iade edilen hammadde. | Ş§1 — Belge (fark türleri Çıkarım) | Z | Üç fark türü de girilebilir ve raporda görünür. | FR-602 |
| FR-110 | EKP = (tüketilen hammadde lotlarının gerçek maliyeti + hizmet maliyeti) / gerçek mamul miktarı. Hesap dökümü saklanır. | Ş§1 — Belge | ★K | Şartname örneği: toplam 1.543,50 €, EKP 18,16 € (tam: 18,1588…), lot değeri 1.543,50 € (18,16 × 85 = 1.543,60 değil). | NFR-001 |
| FR-111 | VKP, brüt kâr (VKP − EKP) ve marj (brüt kâr / VKP) gösterilir. | Ş§1 — Belge (marj tanımı Varsayım AS-002) | Z | Girilen VKP için kâr ve marj doğru hesaplanır. | FR-110 |
| FR-112 | Bütün maliyet ve stok hareketleri geçmişe dönük incelenebilir: kim, ne zaman, hangi belgeyle, hangi lot, ne kadar, hangi tutar. | Ş§1 — Belge | ★K | Herhangi bir lotun tüm hareket geçmişi ve maliyet dökümü listelenebilir. | NFR-002, NFR-008 |

### FR-2xx — Görev 2: Bütün kuzu parçalama

| Kimlik | Gereksinim | Kaynak | Önc. | Tamamlanma ölçütü | İlişki |
|---|---|---|---|---|---|
| FR-201 | Parçalama reçetesi tanımlanır: giriş ürünü (bütün kuzu), çıkış parçaları (but, sırt, omuz, kaburga, kıyma …), yan ürün/fire kalemleri ve beklenen oranlar. | Ş§2 — Belge | Z | Reçete kaydedilir ve parçalama işleminde seçilebilir. | FR-503 (referans yöntem) |
| FR-202 | Dağıtım anahtarı tanımlanır: miktar ağırlıklı veya değer ağırlıklı (parça başına değer katsayısı / satış fiyatı). İşlem başına seçilebilir. | Ş§2 — Belge | ★K | İki yöntem de seçilebilir ve sonuçları farklı/doğru. | FR-206 |
| FR-203 | Parçalama girişi kaydedilir: giriş hayvanı/partisi (lot), ağırlık, gerçek toplam alış maliyeti (kalemli: alış + ek masraflar), işlem tarihi. | Ş§2 — Belge | ★K | Toplam maliyet kalemlerin toplamı olarak hesaplanır. | FR-207 |
| FR-204 | Fiili parça ağırlıkları, fire ve yan ürünler işlem sırasında girilir. | Ş§2 — Belge | ★K | Tüm çıkış kalemleri kaydedilebilir. | FR-205 |
| FR-205 | Ağırlık dengesi kontrol edilir: giriş = parçalar + yan ürün + fire (tanımlı tolerans içinde). Denge yoksa işlem onaylanmaz. | Ş§2 — Belge | ★K | 25 kg giriş / 22 kg parça / fire girilmemiş → reddedilir; 3 kg fire girilince kabul. | CR-012 |
| FR-206 | Maliyet, seçilen anahtara göre parçalara dağıtılır; **dağıtılan toplam = toplam maliyet** (kuruş farkı en büyük kalan yöntemiyle dağıtılır). Fireye maliyet verilmez. | Ş§2 — Belge (kuruş kuralı ve fire Çıkarım/Varsayım AS-006) | ★K | Her iki yöntemde, her girdi için Σ pay = toplam maliyet (kuruşu kuruşuna). | NFR-001 |
| FR-207 | Tutar tutarlılığı kontrol edilir: miktar × birim fiyat ≠ fatura/toplam tutar ise uyarı verilir ve açıklama istenir. | Ş§2 Not — Çıkarım | ★K | 25 × 11,50 = 287,50 ≠ 351,00 → uyarı + açıklama alanı zorunlu. | CR-012 |
| FR-208 | Her parça için giriş lotuna bağlı yeni bir parça lotu açılır ve stoklanır. | Ş§2, Ş§3 — Belge | ★K | Kuzu lotundan bütün parça lotlarına ileri izleme çalışır. | FR-302, FR-401 |

### FR-3xx — Görev 3: Lot izlenebilirliği ve geri çağırma

| Kimlik | Gereksinim | Kaynak | Önc. | Tamamlanma ölçütü | İlişki |
|---|---|---|---|---|---|
| FR-301 | Tedarikçi ve müşteri (market) kartları iletişim bilgileriyle (yetkili, telefon, e-posta, adres) tutulur. | Ş§3 — Çıkarım (iletişim listesi için gerekli) | Z | Geri çağırma listesinde iletişim bilgisi görünür. | FR-307 |
| FR-302 | Lotlar arası **çoktan çoğa** ilişkiler **miktarlarıyla** saklanır (üretim, parçalama, yeniden işleme). | Ş§3 — Belge | ★K | Bir emirde çok girdi lotu, bir lotun çok çıktıya dönüşmesi kaydedilebilir; miktarlar tutarlı. | FR-108, FR-208 |
| FR-303 | Lot bazlı hareket türleri: alış girişi, depo transferi, üretime tüketim, üretimden giriş, parçalama, satış/sevkiyat, iade, yeniden işleme, fire. | Ş§3 — Belge | ★K | Her tür kaydedilebilir; hiçbir hareket lotsuz değildir. | NFR-002 |
| FR-304 | **İleriye izleme:** bir lottan etkilenen bütün türev lotlar (çok adımlı), mevcut stoklar, sevkiyatlar ve bilinen alıcılar miktarlarıyla listelenir. | Ş§3 — Belge | ★K | ET-2026-001 → SUC-2026-045 → A 30 / B 25 / C 30, stok 0. | FR-309 |
| FR-305 | **Geriye izleme:** bir mamul lotundan kullanılan hammadde lotlarına, tedarikçilere ve üretim emirlerine ulaşılır. | Ş§3 — Belge | ★K | SUC-2026-045 → ET-2026-001 + baharat ve bağırsak lotları, tedarikçileri, URT-2026-045. | — |
| FR-306 | Geri çağırma başlatılır: kaynak lot ve ondan türeyen bütün lotlar "bloke" durumuna geçer; geri çağırma kaydı (neden, tarih, başlatan) tutulur. | Ş§3 — Belge | ★K | ET-2026-001 için geri çağırma → SUC-2026-045 de bloke. | FR-310 |
| FR-307 | Geri çağırma listesi üretilir: müşteri/market bazlı miktar, sevkiyat belgeleri, iletişim bilgileri; dışa aktarılabilir. | Ş§3 — Belge (dışa aktarma Çıkarım) | ★K | Liste A/B/C'yi miktar ve iletişimle verir; dosya olarak indirilebilir. | FR-301 |
| FR-308 | İkinci kademe dağıtım, yalnızca kaydedilmişse **kesin** olarak gösterilir; kayıtsızsa "bilinen son alıcı" ve "sonrası bilinmiyor" olarak ayrı işaretlenir. | Ş§3 — Belge | Z | Kayıtlı ve kayıtsız iki örnek doğru ayrılır. | CON-003 |
| FR-309 | Zorunlu senaryo örnek kayıtlarla hazır gelir ve demoda çalışır: ET-2026-001 (100 kg) → URT-2026-045 → SUC-2026-045 (85 paket) → Market A/B/C 30/25/30. | Ş§3, Ş§7, E — Belge | ★K | Temiz kurulumdan sonra senaryo tek adımda sorgulanabilir. | CR-003, CR-009 |
| FR-310 | Bloke lotlar hiçbir kanaldan (web, API, Android) satılamaz, transfer edilemez, üretimde kullanılamaz. | Ş§3 — Belge + Çıkarım | ★K | Bloke lotla yapılan her işlem anlaşılır bir hata ile reddedilir. | FR-403 |

### FR-4xx — Kotlin Android satış/operasyon uygulaması

| Kimlik | Gereksinim | Kaynak | Önc. | Tamamlanma ölçütü | İlişki |
|---|---|---|---|---|---|
| FR-401 | Lot seçerek satış: müşteri, ürün, lot, miktar. Her satış satırı tek bir lot ve tek bir stok hareketiyle eşleşir. | Ş§2, Ş§3 — Belge | ★K | Satış satırı ↔ lot ↔ hareket bağı veritabanında görülebilir. | FR-303 |
| FR-402 | Satılabilir lotlar listelenir; SKT'ye göre "ilk biten ilk çıkar" önerisi yapılır. | Çıkarım | Ö | Liste SKT sırasına göre gelir. | FR-102 |
| FR-403 | Geri çağrılan/bloke lotların satışı engellenir (çevrimiçiyken anlık durumla, çevrimdışıyken son senkron bilgisiyle; sunucu ayrıca kontrol eder). | Ş§3 — Belge | ★K | Bloke lotla satış denemesi cihazda engellenir. | FR-310, R-05 |
| FR-404 | Veriler cihazda SQLite'ta saklanır; bağlantı yokken satış yapılabilir. | Ş§6 — Belge (çevrimdışı satış Çıkarım) | ★K | Uçak modunda satış kaydedilir, bağlantı gelince gönderilir. | FR-405 |
| FR-405 | Senkronizasyon: ana veriler, lot durumları ve stoklar sunucudan cihaza; satışlar cihazdan sunucuya. Tutarlı ve tekrar güvenli (aynı satış iki kez gönderilse tek kayıt). | Ş§6 — Belge | ★K | Çift gönderim testinde tek kayıt; senkron sonrası cihaz ve sunucu stokları eşit. | TR-007 |
| FR-406 | Operasyon ekranları (ör. parçalama tartım girişi, mal kabul) Android'den de yapılabilir. | Ş§6 "satış/operasyon" — Çıkarım | İ | — | FR-204 |

### FR-5xx — Yapay zekâ çalışmaları

| Kimlik | Gereksinim | Kaynak | Önc. | Tamamlanma ölçütü | İlişki |
|---|---|---|---|---|---|
| FR-501 | **Model A:** geçmiş üretim emirlerinden beklenen mamul miktarı (verim) ve birim maliyet (EKP) tahmini. | Ş§4 — Belge | ★K | Yeni emir için tahmin üretilir. | FR-105 |
| FR-502 | Model A için tahmin, gerçek üretim sonucu ve sapma birlikte gösterilir. | Ş§4 — Belge | ★K | Üretim ekranında ve raporda üçlü görünür. | FR-602 |
| FR-503 | **Model B:** hayvan türü, giriş ağırlığı ve geçmiş parçalama kayıtlarından beklenen parça ağırlıkları tahmini. | Ş§4 — Belge | ★K | Parçalama girişinde her parça için beklenen kg görünür. | FR-201 |
| FR-504 | Model B için gerçek miktarlarla farklar raporlanır. | Ş§4 — Belge | ★K | Parçalama raporunda parça bazında tahmin/gerçek/fark. | FR-603 |
| FR-505 | Örnek/anonim veri seti ve üretim varsayımları sunulur. | Ş§4 — Belge | Z | `data/synthetic/` + açıklama belgesi. | AS-011 |
| FR-506 | Basit bir referans yöntemle karşılaştırma ve tahmin hata ölçümü (ör. ortalama mutlak hata, yüzde hata) yapılır. | Ş§4 — Belge | ★K | Ayrılmış test verisinde referans ve model hataları tabloda. | CR-006 |
| FR-507 | Sınırlılıklar açıkça belirtilir (veri azlığı, sentetik verinin etkisi). | Ş§4 — Belge | Z | Değerlendirme raporunda ayrı bölüm. | CR-006 |
| FR-551 | Fatura/irsaliye okuma: ürün, miktar, lot, maliyet öneri olarak çıkarılır; insan onayıyla kaydedilir. | Ş§5 — Belge | İ | — | FR-102 |
| FR-552 | Anomali uyarıları: beklenmedik fire, maliyet artışı, düşük üretim verimi, tutarsız lot hareketleri işaretlenir. | Ş§5 — Belge | İ | — | FR-502, FR-504 |

### FR-6xx — Raporlar

Şartname en az şu raporların **gösterilmesini** istiyor (Ş§6 — Belge). Hepsi web arayüzünde, tarih/ürün/lot süzgeçli.

| Kimlik | Rapor | Önc. | Tamamlanma ölçütü |
|---|---|---|---|
| FR-601 | Alış raporu (tedarikçi, lot, miktar, tutar) | Z | Örnek kayıtlarla dolu görünür. |
| FR-602 | Üretim raporu (emir, girdiler, mamul, farklar, EKP, YZ tahmini/sapma) | Z | URT-2026-045 doğru görünür. |
| FR-603 | Parçalama raporu (giriş, parçalar, fire, dağıtım, YZ tahmini/fark) | Z | Örnek parçalama doğru görünür. |
| FR-604 | Lot hareketleri raporu (lot bazlı tüm hareketler, bakiye) | ★K | Bakiye = hareket toplamı. |
| FR-605 | Satış raporu (müşteri, ürün, lot, miktar, tutar, kanal) | Z | Android satışları görünür. |
| FR-606 | Geri çağırma raporu (etkilenen lotlar, alıcılar, miktarlar, durum) | ★K | ET-2026-001 senaryosu görünür. |
| FR-607 | Bütünlük raporu: defter–özet değişmezleri (`data_model.md` §5, I-1…I-8) tek ekranda denetlenir | Ö | Örnek kayıtlarla bütün değişmezler "tutarlı". |

---

## B. İşlevsel olmayan gereksinimler

| Kimlik | Gereksinim | Kaynak | Önc. | Tamamlanma ölçütü |
|---|---|---|---|---|
| NFR-001 | **Parasal doğruluk:** para ve miktarlar kayan noktalı sayıyla değil ondalık/tamsayı tabanlı tutulur; yuvarlama kuralı tek yerde tanımlıdır; birim maliyet en az 4 ondalıkla saklanır, 2 ondalıkla gösterilir; lot değeri toplam üzerinden tutulur. | Değerlendirme odağı — Çıkarım | ★K | Şartname rakamları testlerde birebir; kuruş farkı yok. |
| NFR-002 | **Değişmez hareket defteri:** stok ve maliyet hareketleri silinmez/güncellenmez; düzeltme ters kayıtla yapılır. | Ş§1 "geçmişe dönük", değerlendirme odağı — Çıkarım | ★K | Hareket silme/güncelleme yolu yok; düzeltme sonrası geçmiş korunur. |
| NFR-003 | **İşlem bütünlüğü:** her iş işlemi (ör. mamul kabulü, parçalama onayı, satış senkronu) tek veritabanı işleminde; yarım kayıt kalmaz. | Değerlendirme odağı — Çıkarım | ★K | Ortada hata verdirilen işlemde hiçbir kayıt kalmaz. |
| NFR-004 | **Stok tutarlılığı:** lot stoku = hareketlerin toplamı; negatif stok engellenir. | Değerlendirme odağı — Çıkarım | ★K | Mutabakat sorgusu her zaman fark 0; eksi stoka düşüren işlem reddedilir. |
| NFR-005 | **Kullanılabilirlik (Android):** satış az adımda tamamlanır; hatalar anlaşılır Türkçe mesajla; çevrimdışı/senkron durumu görünür. | Değerlendirme odağı — Belge | ★K | Ekip dışı bir kişi yardımsız satış yapabilir (kısa deneme). |
| NFR-006 | **Kurulabilirlik:** değerlendirici sistemi README'deki kısa adımlarla (hedef: tek komut) çalıştırır; örnek kayıtlar otomatik yüklenir; hazır APK sunulur. | Ş§7 "çalıştırılabilir prototip" — Çıkarım | ★K | Temiz bir bilgisayarda/klonda README ile kurulum denemesi başarılı. |
| NFR-007 | **Güvenlik:** gizli bilgi depoda yok (`.env.example`); girdi doğrulama; parametreli sorgular; temel kimlik doğrulama. | Çıkarım | Z | Depo taramasında gizli bilgi yok; geçersiz girdiler reddedilir. |
| NFR-008 | **Denetlenebilirlik:** her kaydın oluşturan kullanıcısı ve zamanı tutulur. | Ş§1 — Çıkarım | Z | Hareket listesinde kullanıcı/zaman görünür. |
| NFR-009 | **Performans:** demo ölçeğinde (binlerce hareket) izleme ve geri çağırma sorgusu 2 saniyenin altında. | Varsayım | Ö | Ölçüm sonucu test raporunda. |
| NFR-010 | **Sürdürülebilirlik:** sade katmanlı yapı, anlamlı adlandırma, otomatik testler, kararların kaydı. | "Aday değerlendirme" — Çıkarım | Z | Kod incelemesi + testler + `docs/decisions/`. |

---

## C. Teknik gereksinimler

| Kimlik | Gereksinim | Kaynak | Bağlayıcılık |
|---|---|---|---|
| TR-001 | Android satış/operasyon uygulaması **Kotlin** ile. | Ş§6 — Belge | Zorunlu |
| TR-002 | Yerel veri saklama **SQLite**. | Ş§6 — Belge | Zorunlu |
| TR-003 | Merkezi veri saklama **MySQL**. | Ş§6 — Belge | Zorunlu |
| TR-004 | Backend: **Go** veya uygun modern teknoloji; **REST API**. | Ş§6 — Belge | REST zorunlu, Go önerilen |
| TR-005 | Web yönetim ve raporlama: **React** veya uygun modern web teknolojisi. | Ş§6 — Belge | Önerilen |
| TR-006 | YZ servisleri: uygun ML yaklaşımı ve **API entegrasyonu**. | Ş§6 — Belge | Zorunlu (yöntem serbest) |
| TR-007 | SQLite ↔ MySQL arasında tutarlı senkronizasyon yaklaşımı tasarlanır, uygulanır ve **açıklanır**. | Ş§6 — Belge | Zorunlu |

---

## D. Yarışmaya özgü gereksinimler

| Kimlik | Gereksinim | Kaynak | Önc. |
|---|---|---|---|
| CR-001 | GitHub deposu: kaynak kod + kurulum açıklaması (README); teslim anında **herkese açık**. | E — Belge | ★K |
| CR-002 | Demo videosu: üç görev uçtan uca, **en fazla 15 dk**, bağlantıya sahip herkes izleyebilir (YouTube liste dışı / Drive). | E, Ş§7 — Belge | ★K |
| CR-003 | Demoda özellikle ET-2026-001'den etkilenen marketlerin bulunması gösterilir. | Ş§7, E — Belge | ★K |
| CR-004 | Teslim: 01.11.2026 23:59'a kadar **ext.s.a.bakir@delta-ac.de** adresine (alıcı elle yazılır; ilk e-postaya "yanıtla" ile gönderilenler ulaşmıyor), konu = **Synera**, kayıtlı ekip üyesinin e-postasından; e-postada iki bağlantı. | E1–E3 — Belge | ★K |
| CR-005 | Değerlendirme teslim tarihindeki **son commit** üzerinden yapılır. | E — Belge | ★K |
| CR-006 | YZ yöntemlerinin açıklaması, örnek tahminler ve doğruluk değerlendirmesi teslim edilir. | Ş§4, Ş§7 — Belge | ★K |
| CR-007 | Veri modeli belgesi. | Ş§7 — Belge | Z |
| CR-008 | API açıklaması. | Ş§7 — Belge | Z |
| CR-009 | Örnek kayıtlar. | Ş§7 — Belge | Z |
| CR-010 | Temel otomatik testler. | Ş§7 — Belge | Z |
| CR-011 | Çalıştırılabilir prototip; üç görev ve iki YZ çalışması **entegre**. | Ş§7, Ş amaç — Belge | ★K |
| CR-012 | Görev 2 örnek görselindeki tutarsızlıklar (25 × 11,50 = 287,50 ≠ 351,00; parçalar 22 kg) tespit edilip açıklanır. | Ş§2 Not — Belge | Z |

---

## E. Kısıtlamalar ve varsayımlar

### Kısıtlamalar

| Kimlik | Kısıt | Kaynak |
|---|---|---|
| CON-001 | Süre: 24 Ekim → 1 Kasım 2026 23:59 (≈ 8 gün); 29 Ekim resmî tatil. | E, takvim |
| CON-002 | Kotlin, SQLite, MySQL ve REST API zorunlu. | Ş§6 |
| CON-003 | İzlenebilirlik ve geri çağırma sonuçları YZ tahminine değil, kesin kayıt ilişkilerine dayanır. | Ş§4 |
| CON-004 | Gerçek veri yok (bkz. AS-011) → örnek/anonim veri. | Ş§4 |
| CON-005 | Video en fazla 15 dakika. | E |
| CON-006 | Depo herkese açık olacak: gizli bilgi ve yarışma belgeleri depoya girmez. | E |
| CON-007 | Geliştirme ortamı eksikleri: bu bilgisayarda Android Studio/SDK ve JDK yok, Docker Desktop kapalı; Windows Uygulama Denetimi daha önce scikit-learn'ü engelledi. | 24 Ekim tespiti |
| CON-008 | Ekip Go bilmiyor; sunucu tarafında Kotlin veya Python kullanılacak. | Ekip cevabı, 24 Ekim |

### Varsayımlar (cevap gelene kadar geçerli)

| Kimlik | Varsayım | İlgili soru |
|---|---|---|
| AS-001 | Tutarlar KDV hariç (net), tek para birimi €. | S-07 |
| AS-002 | Marj = brüt kâr / VKP (satış üzerinden). | S-07 |
| AS-003 | Narin Sucuk 1 paket = 1 kg. | (Belge: "85 adet 1 kg") |
| AS-004 | Baharat ve bağırsak lot numaralarını biz tanımlarız. | — |
| AS-005 | Sucuk ve parçaların satış fiyatlarını (VKP) demo için biz belirleriz. | — |
| AS-006 | Fireye maliyet dağıtılmaz; yan ürünlerin maliyet payı reçetede tanımlanır (0 olabilir). | — |
| AS-007 | Verim, et bazlı (mamul / et) tahmin edilir; toplam girdi bazlı verim de gösterilir. | S-08 |
| AS-008 | Market A/B/C'ye sevkiyat Kotlin uygulamasından satış olarak kaydedilir. | S-09 |
| AS-009 | Değerlendirici sistemi kendi bilgisayarında (Docker ile) çalıştırır; Android için hazır APK sunulur. | — |
| AS-010 | Teslim saati Türkiye saati (daha erken olan) kabul edilir. | S-04 |
| AS-011 | Gerçek üretim/parçalama verisi yok (**ekip teyit etti, 24 Ekim**); YZ için belgelenmiş varsayımlarla sentetik veri üretilir. | S-11 |
