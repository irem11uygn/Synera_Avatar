# Teslim Kontrol Listesi

> Durum (27 Ekim 2026): içerik maddeleri hazır ve denetlendi (kabul testleri 23/23, `reports/kabul_testleri.md`). Kalanlar: son commit, GitHub'a yükleme ve herkese açma, APK'nın Releases'e eklenmesi, video, e-posta.

Son teslim: **1 Kasım 2026 23:59** (Türkiye saati esas). Hedef: 1 Kasım öğleden sonra.
Kaynak: yarışma e-postası ve şartname §7. Kimlikler `requirements.md`'den.

## Depo (CR-001, CR-005)

- [x] Kaynak kodun tamamı depoda; son commit teslimden önce atıldı
- [x] README: proje özeti, kurulum, çalıştırma, demo hesapları, bilinen sınırlamalar
- [ ] Depo **herkese açık** (gizli pencerede açılarak denendi)
- [x] Depoda gizli bilgi yok (`.env` yok, yalnız `.env.example`); `_kaynak/` gönderilmedi
- [ ] Android APK indirilebilir (Release veya depo içi)

## İçerik (CR-006 … CR-012)

- [x] Veri modeli belgesi (ER diyagramı + tablolar) — CR-007
- [x] API açıklaması — CR-008
- [x] Örnek kayıtlar otomatik yükleniyor — CR-009
- [x] Temel otomatik testler çalışıyor; sonuçları `reports/test_results.md`'de — CR-010
- [x] YZ yöntem açıklaması, örnek tahminler, referans yöntemle karşılaştırma, hata ölçümü, sınırlılıklar — CR-006
- [x] SQLite ↔ MySQL senkronizasyon açıklaması — TR-007
- [x] Görev 2 tutarsızlık açıklaması — CR-012
- [x] Altı rapor gösterilebiliyor (alış, üretim, parçalama, lot hareketleri, satış, geri çağırma) — FR-601…606

## Video (CR-002, CR-003)

- [ ] Süre ≤ 15 dakika
- [ ] Görev 1, 2 ve 3 uçtan uca gösterildi; iki YZ modeli gösterildi
- [ ] ET-2026-001'den etkilenen marketlerin (A 30 / B 25 / C 30) bulunması açıkça gösterildi
- [ ] Kotlin uygulamasıyla satış ve geri çağrılan lotun satış engeli gösterildi
- [ ] YouTube "liste dışı" veya Drive; **bağlantıya sahip herkes izleyebiliyor** (oturum kapalı tarayıcıda denendi)

## E-posta (CR-004) — ekip gönderir

- [ ] Kayıtlı bir ekip üyesinin e-posta adresinden
- [ ] Alıcı: **ext.s.a.bakir@delta-ac.de** — elle yazıldı (20 Ekim e-postasına göre ilk e-postaya "yanıtla" ile gönderilenler ulaşmıyor)
- [ ] Konu satırı: **Synera**
- [ ] İki bağlantı: GitHub deposu + demo videosu
- [ ] Gönderildi (tarih/saat): ……
