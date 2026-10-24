# ADR-005: Yapay zekâ — scikit-learn, referans yöntemler, zaman bazlı değerlendirme, sentetik veri

- Durum: **Kabul edildi** (ekip onayı: 24.10.2026)
- Tarih: 24.10.2026
- İlgili gereksinimler: FR-501–507, CR-006, CON-003, AS-011
- Ayrıntı: `docs/technical_research.md` §6 (D-05)

## Bağlam
İki zorunlu model isteniyor: (A) üretim verimi ve EKP, (B) parçalama verimi. Şartname referans yöntemle karşılaştırma, hata ölçümü ve sınırlılıkların açıkça yazılmasını şart koşuyor. Gerçek veri yok.

## Seçenekler
- Kütüphane: **scikit-learn** / statsmodels / LightGBM–XGBoost / derin öğrenme / büyük dil modeli
- Veri: **belgelenmiş sentetik veri** / kamuya açık veri seti (bu alana uygun, lot düzeyinde açık veri bilinmiyor)

## Karar
- scikit-learn ile doğrusal (Ridge) ve ağaç tabanlı (HistGradientBoosting) modeller karşılaştırılır; model seçimi zaman sıralı çapraz doğrulamayla yapılır.
- **Model A:** et bazlı verim tahmin edilir; EKP tahmini, bilinen hammadde maliyeti + tahmini paket sayısından hesaplanır. Referans yöntem: ürün bazında geçmiş ortalama verim.
- **Model B:** parça payları tahmin edilip toplamı 1 olacak biçimde ölçeklenir. Referans yöntem: reçete oranı × giriş ağırlığı.
- **Değerlendirme:** kronolojik %80/%20 ayırma; MAE, MAPE ve referansa göre iyileşme; tahmin, emir açılırken kaydedilir.
- **Veri:** sabit tohumlu, etkileri parametre olarak açıkça yazılmış sentetik üretici.

## Sonuçlar
- "Ölçülebilir katkı" tek tabloda gösterilir: referans hatası, model hatası, iyileşme yüzdesi.
- Sentetik veride ölçülen başarı gerçek işletmenin kanıtı değildir; bu sınırlılık raporda ayrı bölümde yazılır.
- İzleme ve geri çağırma hiçbir yerde model çıktısı kullanmaz (CON-003).
