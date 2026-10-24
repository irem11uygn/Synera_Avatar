# Test Stratejisi

| | |
|---|---|
| Sürüm | v0.1 (kabul testleri şartnameden çıkarıldı; araçlar ve komutlar Aşama 4–5'te eklenecek) |
| Tarih | 24 Ekim 2026 |

**Kural:** Çalıştırılmamış hiçbir test "geçti" olarak işaretlenmez. Her çalıştırmanın sonucu (tarih, komut, çıktı özeti) `reports/test_results.md` dosyasına yazılır.

## 1. Test seviyeleri

| Seviye | Neyi doğrular | Nerede | Ne zaman çalışır |
|---|---|---|---|
| Birim | Maliyet motoru, dağıtım, ağırlık dengesi, lot ağı gezinmesi, senkron kuyruğu | Her bileşenin kendi klasörü | Her değişiklikte |
| Entegrasyon | API + gerçek MySQL (Docker), veritabanı işlemleri, kısıtlar | `backend/` | Her akşam birleştirmede |
| Kabul (uçtan uca) | Şartname senaryoları (aşağıdaki AT listesi) | `tests/` | Her akşam + teslim öncesi |
| Android | Yerel SQLite, satış akışı, bloke engeli, senkron | `android/` | Her akşam |
| YZ değerlendirme | Ayrılmış test verisinde referans yönteme karşı hata | `ml/` → `reports/` | Model değiştikçe |
| Elle / kullanılabilirlik | Demo akışı, ekip dışı bir kişinin satış denemesi | — | M4 ve M5'te |
| Kurulum | Temiz klonda README ile kurulum | — | T-26 |

## 2. Kabul testleri (şartnameden)

Beklenen değerler şartnameden (**Belge**) veya bizim tanımladığımız örnekten (**Örnek**) gelir.

| Kimlik | Senaryo | Beklenen sonuç | Kaynak | Doğruladığı gereksinimler | Durum |
|---|---|---|---|---|---|
| AT-01 | Narin Sucuk dış üretimi: 100 kg et × 9,70; 2 kg baharat × 24,00; 5 kg bağırsak × 11,60; 85 paket × 5,50 hizmet; 85 paket kabul | Toplam 1.543,50 €; EKP gösterimi 18,16 € (saklanan ≥ 18,1588); lot değeri 1.543,50 € | Belge | FR-107, FR-108, FR-110, NFR-001 | Geçti (24.10): üretim emri API'den baştan sona (`test_production::test_at01_*`) ve çalışan sistemde gerçek HTTP ile; maliyet hesabı ayrıca `test_costing` |
| AT-02 | AT-01 + VKP 24,90 € | Brüt kâr 6,74 €; marj %27,07 | Örnek (VKP bizim) | FR-111, AS-002 | Geçti (24.10, `test_costing`) |
| AT-03 | Kuzu parçalama, toplam 351,00 €, parçalar but 7 / sırt 4 / omuz 5 / kaburga 3 / kıyma 3 kg, fire 3 kg | Miktar ağırlıklı: 111,68 / 63,82 / 79,77 / 47,87 / 47,86 (eşit kalanlarda reçete sırası); değer ağırlıklı (22/26/18/14/16 €/kg): 123,41 / 83,34 / 72,12 / 33,66 / 38,47; ikisinde de toplam **351,00** | Örnek (`project_analysis.md` §3.3) | FR-202, FR-206, NFR-001 | Geçti (24.10, `test_allocation`); parçalama onay akışı T-11 |
| AT-04 | 25 kg giriş, 22 kg parça, fire girilmemiş | İşlem onaylanmaz, fark (3 kg) gösterilir; 3 kg fire girilince onaylanır | Belge (not) | FR-205, CR-012 | Hesap geçti (24.10, `test_balance_and_graph`); onayın reddi T-11 |
| AT-05 | 25 kg × 11,50 € girildi, fatura toplamı 351,00 € | Uyarı + açıklama zorunlu; açıklamasız kayıt reddedilir | Belge (not) | FR-207, CR-012 | Geçti (24.10): alış servisi + veritabanı kısıtı (`test_purchasing`, `test_schema`) |
| AT-06 | ET-2026-001 için ileri izleme | SUC-2026-045; Market A 30, B 25, C 30 paket; depoda kalan 0; sevkiyat belgeleri ve iletişim | Belge | FR-304, FR-309, CR-003 | Kısmen geçti (24.10): lot ağı ileri izleme (`test_ledger`); alıcı listesi T-16 |
| AT-07 | SUC-2026-045 için geri izleme | ET-2026-001 + baharat ve bağırsak lotları, tedarikçileri, URT-2026-045 | Belge | FR-305 | Kısmen geçti (24.10): lot ağı geri izleme (`test_ledger`); tedarikçi/emir dökümü T-16 |
| AT-08 | ET-2026-001 için geri çağırma | SUC-2026-045 bloke; web, API ve Android'den satış/transfer reddedilir; liste A/B/C'yi miktar + iletişimle verir ve dışa aktarılır | Belge | FR-306, FR-307, FR-310, FR-403 | Kısmen geçti (24.10): defter bloke lotta satış/transferi reddediyor (`test_ledger`); geri çağırma akışı T-16, Android T-14 |
| AT-09 | İkinci kademe: Market B'nin şubelerine dağıtımı kayıtlı, A ve C'ninki kayıtsız | B'nin şubeleri "kesin"; A ve C "bilinen son alıcı, sonrası bilinmiyor" | Belge + Örnek | FR-308 | Yazılmadı |
| AT-10 | Hareket defteri | Hareket silinemez/güncellenemez; düzeltme ters kayıtla; lot stoku = Σ hareket; eksi stoka düşüren işlem reddedilir; yarıda hata veren işlem hiç kayıt bırakmaz | Çıkarım | NFR-002, NFR-003, NFR-004 | Geçti (24.10): değişmez defter, ters kayıt, eksi stok reddi, I-1…I-8 denetimi (`test_ledger`, `test_integrity`, `test_schema`). Eşzamanlı satış kilidi henüz test edilmedi |
| AT-11 | Aynı satış senkronda iki kez gönderilir | Sunucuda tek satış, tek stok hareketi | Çıkarım | FR-405 | Yazılmadı |
| AT-12 | Cihaz çevrimdışıyken lot geri çağrılır, cihaz o lottan satış yapar, sonra bağlanır | Mimaride kararlaştırılacak kurala göre (öneri: satış kaydedilir + uyarı üretilir + geri çağırma listesine eklenir) | Çıkarım | FR-403, FR-405 | Kural bekleniyor |
| AT-13 | YZ değerlendirmesi (Model A ve B) | Ayrılmış test verisinde referans yöntem ve model hataları raporlanır; hedef: model < referans. Hedefe ulaşılmazsa dürüstçe raporlanır | Belge | FR-501–507, CR-006 | Yazılmadı |
| AT-14 | Temiz klonda kurulum | README adımlarıyla sistem ayağa kalkar, örnek kayıtlar yüklü, AT-06 arayüzden yapılabilir | Çıkarım | NFR-006, CR-001, CR-011 | Yazılmadı |
| AT-15 | Dış üretimde miktar farkı: planlanan 87, teslim 85 paket; 0,5 kg baharat iade | Farklar emirde ve üretim raporunda görünür; EKP teslim edilen 85'e göre | Örnek | FR-109, FR-602 | Kısmen geçti (24.10): farklar emirde, iade ana depoya döner, EKP 85'e göre 18,02 € (`test_production::test_at15_*`); web emir ekranında plan/teslim farkı, tüketim/iade ve fatura farkı görünür (T-10, elle); üretim raporu T-22 |

**Tasarım doğrulaması (24 Ekim 2026):** AT-01, AT-03, AT-04, AT-06, AT-07, AT-08 (yalnız bloke durumu), AT-10 ve AT-11 senaryoları, veri modelinin sade bir kopyasında çalıştırıldı ve 20/20 kontrol geçti (`reports/design_validation/`). Bu sonuç tasarımın mantığını doğrular; yukarıdaki ürün testlerinin durumu bu yüzden hâlâ "Yazılmadı"dır. AT-10'un denetleyeceği değişmezler: `data_model.md` §5 (I-1…I-8).

## 3. Gereksinim → test izleme

Yukarıdaki tablonun "Doğruladığı gereksinimler" sütunu izleme matrisidir. Testi olmayan ★K gereksinimler, mimari tasarımdan sonra birim/entegrasyon testleriyle eşlenecek ve bu bölüme eklenecek.

## 4. Araçlar ve komutlar

| Ne | Komut | Durum |
|---|---|---|
| Sunucu testleri (gerçek MySQL ile) | `docker compose run --rm --no-deps api pytest -v` | Çalışıyor |
| Python denetim + biçim | `docker compose run --rm --no-deps api sh -c "ruff check . && ruff format --check ."` | Çalışıyor |
| Web tip denetimi + derleme | `cd web && npm run build` | Çalışıyor |
| Web kod denetimi | `cd web && npx oxlint` | Çalışıyor |
| Web birim testleri (Vitest) | `cd web && npm test` | Çalışıyor (ondalık hesap, biçimler, yol eşleme) |
| Web API tiplerini yenileme | `cd web && npm run api:types` (önce `docs/openapi.json` güncellenir) | Çalışıyor |
| Web uçtan uca (elle) | Tarayıcıda Görev 1 senaryosu | T-10'da elle denendi; otomatik arayüz testi yok |
| Kabul testleri (`tests/`) | — | T-23'te |
| Android birim testleri (JUnit) | `cd android && ./gradlew testDebugUnitTest` (JAVA_HOME = Android Studio JDK) | Çalışıyor |
| Android derleme | `cd android && ./gradlew assembleDebug` | Çalışıyor |
| Android uçtan uca (elle/adb) | Emülatörde giriş → eşitleme → araç stoku; bloke lot işareti | T-13'te elle denendi; otomatik arayüz testi yok |

Her çalıştırmanın sonucu `reports/test_results.md`'ye yazılır.
