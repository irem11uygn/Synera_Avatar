# ADR-006: Para ve miktar gösterimi, yuvarlama kuralları

- Durum: **Kabul edildi** (ekip onayı: 24.10.2026)
- Tarih: 24.10.2026
- İlgili gereksinimler: NFR-001, FR-110, FR-206, AT-01, AT-03
- Ayrıntı: `docs/technical_research.md` §7 (D-06)

## Bağlam
"Doğru maliyet hesabı" değerlendirme ölçütü. Şartname örneğinde bile yuvarlama farkı var: 18,16 € × 85 = 1.543,60 €, gerçek toplam 1.543,50 €. Parçalama dağıtımında düz yuvarlama toplamı 1 kuruş saptırıyor.

## Seçenekler
1. **Sunucuda `Decimal`, MySQL'de `DECIMAL`, Android'de tamsayı, JSON'da metin.**
2. Her katmanda tamsayı kuruş — doğru ama birim maliyet gibi çok ondalıklı değerlerde ölçek takibi karmaşık.
3. Kayan noktalı sayı — reddedildi (yuvarlama hataları).

## Karar
Seçenek 1:
- Defter tutarları `DECIMAL(14,2)`, birim maliyet `DECIMAL(14,6)` (yalnız bilgi ve gösterim), miktar `DECIMAL(12,3)`.
- Lot değeri kuruşların toplamıdır. Çıkışta maliyet = kalan değer × çıkan miktar / kalan miktar; **son çıkış kalanın tamamını alır**.
- Maliyet dağıtımında en büyük kalan yöntemi kullanılır; eşitlikte reçete sırası belirler.
- Yuvarlama tek bir fonksiyonda, ticari yuvarlama (yarım yukarı) ile yapılır.
- JSON'da ondalıklar metin taşınır; Android SQLite'ta kuruş ve gram/adet tamsayı tutulur.

## Sonuçlar
- Toplamlar hiçbir zaman birim maliyetten geri hesaplanmaz; kuruş kayması olmaz.
- Web ve Android tarafında metin ↔ ondalık dönüşümü için küçük yardımcılar gerekir.
