# ml/

Yapay zekâ çalışmaları: (A) üretim verimi ve EKP tahmini, (B) parçalama verimi tahmini. Bu klasörde örnek veri üretimi, model eğitimi, referans yöntemle karşılaştırma ve hata ölçümü yer alır. Tahminleri sunucu (`backend/`) bu paketi içe aktararak kendi API'sinden sunar.

**Durum:** Henüz kod yok. Önerilen yaklaşım: scikit-learn, zaman bazlı değerlendirme, belgelenmiş sentetik veri (`docs/decisions/ADR-005`, onay bekliyor). Değerlendirme raporları `reports/` altına yazılacak.

İlgili gereksinimler: `docs/requirements.md` → FR-5xx, TR-006, CR-006.
