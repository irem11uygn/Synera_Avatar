# ml/

Yapay zekâ çalışmaları: (A) üretim verimi ve EKP tahmini, (B) parçalama verimi tahmini. Bu klasörde örnek veri üretimi, model eğitimi, referans yöntemle karşılaştırma ve hata ölçümü yer alır. Tahminleri sunucu (`backend/`) bu paketi içe aktararak kendi API'sinden sunar.

**Durum (27 Ekim):** Henüz kod yok. Bu klasörün sahibi Kişi 2'dir (`docs/is_bolumu.md`). Yöntem kararı kabul edildi: `docs/decisions/ADR-005-yapay-zeka-yaklasimi.md`. Sunucuya bağlanma sözleşmesi: `docs/is_bolumu.md` §6 ve `docs/architecture.md` §6.

Önerilen yapı (`docs/architecture.md` §12):

| Yol | Amaç |
|---|---|
| `avatar_ml/data_gen.py` | Sabit tohumlu sentetik geçmiş: dış üretim emirleri ve parçalamalar (T-18); çıktı `data/synthetic/` |
| `avatar_ml/features.py` | Özellik çıkarımı (eğitimde ve sunucudaki tahminde aynı kod) |
| `avatar_ml/train.py`, `evaluate.py` | Eğitim; kronolojik %80/%20, MAE ve MAPE, referans yöntemle karşılaştırma (T-19, T-20) |
| `avatar_ml/predict.py` | Sunucunun çağıracağı tahmin fonksiyonları |
| `models/` | Eğitilmiş küçük model dosyaları ve `metadata.json` (sürüm, eğitim tarihi, hata ölçümleri); depoya girer |

Not: Kişi 1'in bilgisayarında Windows Uygulama Denetimi scikit-learn'ü engelliyor; eğitim ve testler Docker içinde (Linux) çalıştırılabilir. Değerlendirme raporu `reports/ai_degerlendirme.md` olacak.

İlgili gereksinimler: `docs/requirements.md` → FR-501…FR-507, TR-006, CR-006.
