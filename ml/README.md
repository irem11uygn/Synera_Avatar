# ml/

Yapay zekâ çalışmaları:
- **Model A:** üretim verimi ve EKP tahmini.
- **Model B:** parçalama verimi tahmini.

Bu klasörde sentetik veri üretimi, model eğitimi, referans yöntemle karşılaştırma ve hata ölçümü yer alır. Sunucu (`backend/`) bu paketi `avatar_ml` adıyla içe aktarır ve tahminleri kendi API'sinden sunar (`backend/app/services/ai.py`).

**Sonuçlar ve yöntem:** [reports/ai_degerlendirme.md](../reports/ai_degerlendirme.md) · Karar: [ADR-005](../docs/decisions/ADR-005-yapay-zeka-yaklasimi.md)

| Yol | Amaç |
|---|---|
| `avatar_ml/data_gen.py` | Sabit tohumlu sentetik geçmiş (T-18); çıktı `data/synthetic/` |
| `avatar_ml/features.py` | Özellik çıkarımı; eğitimde ve sunucudaki tahminde aynı kod |
| `avatar_ml/train.py` | Eğitim ve değerlendirme (T-19, T-20): kronolojik %80/%20, zaman sıralı çapraz doğrulamayla model seçimi, MAE ve MAPE, referansla karşılaştırma |
| `avatar_ml/predict.py` | Sunucunun çağırdığı tahmin fonksiyonları |
| `models/` | Eğitilmiş modeller (`model_a.joblib`, `model_b.joblib`) ve `metadata.json` (sürüm, eğitim zamanı, ölçümler, örnek tahminler, sınırlılıklar); depoya dahil, değerlendiricinin yeniden eğitmesi gerekmez |
| `tests/` | Veri tekrarlanabilirliği, ağırlık dengesi, modelin referansla aynı satırlarda ölçülmesi |

Yeniden üretme ve test komutları: `reports/ai_degerlendirme.md` §8. Eğitim Docker içinde (Linux) çalışır; kütüphane sürümleri `backend/requirements.txt`'te sabittir (scikit-learn 1.8.0). Model dosyası aynı sürümle açılmalıdır.
