# Sentetik geçmiş veri (FR-505)

Gerçek işletme verisi olmadığı için yapay zekâ modelleri bu dosyalarla eğitilir ve ölçülür. Dosyaları `ml/avatar_ml/data_gen.py` üretir. Tohum sabittir (2026); aynı komut her çalıştırmada aynı veriyi üretir. Bütün varsayımlar o dosyanın başında ve `reports/ai_degerlendirme.md` §3'te yazılıdır.

| Dosya | Satır | İçerik |
|---|---|---|
| `production_history.csv` | 240 | Geçmiş dış üretim emirleri: dış üretici, et tedarikçisi, et/baharat/bağırsak kg, etin bekleme günü, et birim fiyatı, hammadde maliyeti, hizmet ücreti, mamul kg, paket sayısı, et bazlı verim, EKP |
| `cutting_history.csv` | 300 | Geçmiş parçalamalar: tür, tedarikçi, giriş kg; but, sırt, omuz, kaburga, kıyma ve fire kg'ları (toplamları girişe eşit) |

Adlar ve kodlar uydurmadır; kişisel veri yoktur. Sistemdeki örnek kayıtlarla aynı kodlar kullanılır (FSN-01, TED-ET, TED-KUZU), böylece uygulamadaki gerçek emirler için de anlamlı tahmin yapılır.
