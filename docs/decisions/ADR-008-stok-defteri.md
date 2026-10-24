# ADR-008: Stok defteri — değişmez hareketler, kilitli özetler, lot düzeyinde değerleme

- Durum: **Kabul edildi** (ekip onayı: 24.10.2026)
- Tarih: 24.10.2026
- İlgili gereksinimler: NFR-002, NFR-003, NFR-004, FR-112, FR-303, FR-607, AT-10
- Ayrıntı: `docs/architecture.md` §3.1–3.2, `docs/data_model.md` §3 ve §5

## Bağlam
"Güvenilir stok hareketleri" ve "doğru maliyet hesabı" değerlendirme ölçütleri. Stok, geçmişe dönük incelenebilmeli; eşzamanlı işlemler eksi stok veya çift düşüm üretmemeli; satılan malın maliyeti lot değerinden kuruş kaymadan düşmeli.

## Seçenekler
1. **Yalnız eklenen hareket defteri + aynı işlemde güncellenen özetler (lot ve lot×depo) + satır kilidi.**
2. Yalnız defter, bakiye her seferinde toplamdan hesaplanır — sade, ama eksi stok denetimi için yine kilit gerekir ve her okuma pahalılaşır.
3. Yalnız bakiye tablosu (hareketsiz) — geçmiş kaybolur; şartnameyi karşılamaz.

Değerleme için:
- a) **Lot düzeyinde gerçek değer; transfer değersiz; son çıkış kalanı alır.**
- b) Hareketli ağırlıklı ortalama — "gerçek maliyet" vurgusuyla çelişir, lot bazlı geri çağırma maliyetini bulanıklaştırır.

## Karar
1 + a:
- `stock_movements` yalnız eklenir; MySQL tetikleyicileri UPDATE/DELETE'i engeller; düzeltme ters kayıtla yapılır.
- Bütün yazımlar `ledger.post()` üzerinden geçer: lot/ürün/depo zorunlu, bloke denetimi, eksi stok denetimi, değerleme, özet güncellemesi.
- Kilit sırası: lot satırı → bakiye satırı.
- Değerli çıkış = kalan değer × miktar / kalan miktar (kuruşa yuvarlanmış); lotu sıfırlayan çıkış kalan değerin tamamını alır. Transfer değer taşımaz.
- Değişmezler I-1…I-8 bütünlük raporuyla (FR-607) her an denetlenebilir.

## Sonuçlar
- Satış maliyetleri toplamı lot değerine kuruşu kuruşuna eşit. Tasarım doğrulamasında 544,76 + 453,97 + 544,77 = 1.543,50 € çıktı.
- Defter ile özetlerin uyumu, kodun her yazım yolunda tek fonksiyonu kullanmasına bağlı. Bu, kod incelemesi ve bütünlük testleriyle korunur.
- Depo bazında "değer" doğrudan tutulmaz; gerekirse miktar × lot birim değeriyle yaklaşık raporlanır.
- (T-06'da görüldü) MySQL 8.4'te ikili günlük açıkken yönetici olmayan uygulama kullanıcısı tetikleyici oluşturamıyor (hata 1419). Bu yüzden MySQL `--log-bin-trust-function-creators=1` ile başlatılıyor (`docker-compose.yml`). Tetikleyiciler yalnız hata verdiği için bu ayar güvenli. Gerçek bir kurulumda tetikleyiciler yönetici hesabıyla oluşturulabilir.
- (T-09'da görüldü) Bağlantılar READ COMMITTED yalıtımıyla açılıyor. MySQL'in varsayılanı REPEATABLE READ'de bir işlem ilk okumadaki anlık görüntüyü görmeye devam ediyor; kilitli okuma ile düz okuma farklı sonuç verebiliyordu. Defterin doğruluğu zaten satır kilitlerine (önce lot, sonra bakiye) dayandığı için bu düzey yeterli ve daha öngörülebilir.
