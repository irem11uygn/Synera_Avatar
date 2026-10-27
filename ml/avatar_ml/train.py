"""Model A ve B eğitimi ve değerlendirmesi (T-19, T-20; FR-501, FR-503, FR-506; ADR-005).

Yöntem:
1. Veri tarihe göre sıralanır; ilk %80 eğitim, son %20 test (kronolojik ayırma — gelecekten sızma yok).
2. Eğitim kısmında zaman sıralı 5 katlı çapraz doğrulamayla Ridge ve HistGradientBoosting karşılaştırılır;
   ortalama hatası düşük olan seçilir.
3. Seçilen yöntem eğitim kısmında eğitilir, test kısmında referans yöntemle birlikte ölçülür (MAE, MAPE).
4. Sunulacak model aynı yöntemle bütün veride yeniden eğitilir ve ml/models/ altına yazılır;
   ölçümler ve örnek tahminler metadata.json'a yazılır.

Referans yöntemler:
- Model A: eğitim verisindeki ortalama et bazlı verim (ürün bazında geçmiş ortalama; tek mamul var).
- Model B: reçetedeki standart oran × giriş ağırlığı.

Çalıştırma: python -m avatar_ml.train
"""

import json
import math
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

import joblib
import numpy as np
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.linear_model import Ridge
from sklearn.model_selection import TimeSeriesSplit
from sklearn.multioutput import MultiOutputRegressor
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from avatar_ml import data_gen
from avatar_ml.features import (
    CUTTING_CATEGORICAL,
    CUTTING_NUMERIC,
    PRODUCTION_CATEGORICAL,
    PRODUCTION_NUMERIC,
    CuttingFeatures,
    ProductionFeatures,
    categories_of,
    cutting_matrix,
    feature_names,
    production_matrix,
)

MODELS_DIR = Path(__file__).resolve().parents[1] / "models"
VERSION = "1.0.0"
TEST_SHARE = 0.2
STANDARD_SHARES = dict(zip(data_gen.PARTS, data_gen.SPECIES_BASE["KUZU"], strict=True))  # reçete KUZU-STD


def candidates(multi_output: bool) -> dict[str, Any]:
    hgb = HistGradientBoostingRegressor(
        max_iter=200, learning_rate=0.05, max_leaf_nodes=15, min_samples_leaf=10, random_state=0
    )
    return {
        "Ridge": make_pipeline(StandardScaler(), Ridge(alpha=1.0)),
        "HistGradientBoosting": MultiOutputRegressor(hgb) if multi_output else hgb,
    }


def _mae(errors: np.ndarray) -> float:
    return float(np.mean(np.abs(errors)))


def _mape(actual: np.ndarray, predicted: np.ndarray) -> float:
    mask = actual != 0
    return float(np.mean(np.abs((actual[mask] - predicted[mask]) / actual[mask])) * 100)


def _improvement(baseline: float, model: float) -> float:
    return round((baseline - model) / baseline * 100, 1) if baseline else 0.0


def _select(name_to_model: dict[str, Any], x: np.ndarray, y: np.ndarray) -> tuple[str, dict[str, float]]:
    """Zaman sıralı çapraz doğrulama; her aday için ortalama MAE, en düşüğü seçilir."""
    scores = {}
    for name, model in name_to_model.items():
        errors = []
        for train_idx, valid_idx in TimeSeriesSplit(n_splits=5).split(x):
            fitted = model.fit(x[train_idx], y[train_idx])
            errors.append(_mae(fitted.predict(x[valid_idx]) - y[valid_idx]))
        scores[name] = round(float(np.mean(errors)), 6)
    return min(scores, key=lambda k: scores[k]), scores


# --- Model A ---


def production_rows(rows: list[dict]) -> tuple[list[ProductionFeatures], np.ndarray, list[dict]]:
    features = [
        ProductionFeatures(
            subcontractor=r["subcontractor"],
            meat_supplier=r["meat_supplier"],
            meat_kg=float(r["meat_kg"]),
            spice_kg=float(r["spice_kg"]),
            casing_kg=float(r["casing_kg"]),
            meat_age_days=int(r["meat_age_days"]),
            month=date.fromisoformat(r["order_date"]).month,
        )
        for r in rows
    ]
    return features, np.array([float(r["yield_main"]) for r in rows]), rows


def packages_from_yield(meat_kg: float, yield_main: float) -> int:
    return max(1, math.floor(meat_kg * yield_main / data_gen.PACKAGE_KG))


def ekp(raw_material_cost: float, service_unit_price: float, packages: int) -> float:
    return (raw_material_cost + service_unit_price * packages) / packages


def train_model_a(rows: list[dict]) -> tuple[dict, dict]:
    features, target, raw = production_rows(rows)
    split = int(len(rows) * (1 - TEST_SHARE))
    categories = categories_of(features[:split], PRODUCTION_CATEGORICAL)
    x_train = production_matrix(features[:split], categories)
    x_test = production_matrix(features[split:], categories)
    algorithm, cv = _select(candidates(False), x_train, target[:split])
    model = candidates(False)[algorithm].fit(x_train, target[:split])

    baseline_yield = float(np.mean(target[:split]))
    predicted_yield = model.predict(x_test)
    test = raw[split:]
    actual_packages = np.array([int(r["packages"]) for r in test])
    actual_ekp = np.array([float(r["ekp"]) for r in test])

    def evaluate(yields: np.ndarray) -> dict[str, float]:
        packages = np.array(
            [packages_from_yield(f.meat_kg, y) for f, y in zip(features[split:], yields, strict=True)]
        )
        ekps = np.array(
            [
                ekp(float(r["raw_material_cost"]), float(r["service_unit_price"]), int(p))
                for r, p in zip(test, packages, strict=True)
            ]
        )
        return {
            "yield_mae_pp": round(_mae(yields - target[split:]) * 100, 3),
            "packages_mae": round(_mae(packages - actual_packages), 3),
            "packages_mape_pct": round(_mape(actual_packages, packages), 3),
            "ekp_mae_eur": round(_mae(ekps - actual_ekp), 4),
            "ekp_mape_pct": round(_mape(actual_ekp, ekps), 3),
        }

    baseline_metrics = evaluate(np.full(len(test), baseline_yield))
    model_metrics = evaluate(predicted_yield)
    samples = [
        {
            "order_no": r["order_no"],
            "order_date": r["order_date"],
            "subcontractor": r["subcontractor"],
            "meat_supplier": r["meat_supplier"],
            "meat_kg": float(r["meat_kg"]),
            "actual_packages": int(r["packages"]),
            "baseline_packages": packages_from_yield(f.meat_kg, baseline_yield),
            "model_packages": packages_from_yield(f.meat_kg, float(y)),
            "actual_ekp": round(float(r["ekp"]), 2),
            "model_ekp": round(
                ekp(
                    float(r["raw_material_cost"]),
                    float(r["service_unit_price"]),
                    packages_from_yield(f.meat_kg, float(y)),
                ),
                2,
            ),
        }
        for r, f, y in list(zip(test, features[split:], predicted_yield, strict=True))[-8:]
    ]

    full_categories = categories_of(features, PRODUCTION_CATEGORICAL)
    final = candidates(False)[algorithm].fit(production_matrix(features, full_categories), target)
    bundle = {
        "model": final,
        "categories": full_categories,
        "algorithm": algorithm,
        "version": f"A-{VERSION}",
        "baseline_yield": float(np.mean(target)),
    }
    meta = {
        "version": bundle["version"],
        "target": "Et bazlı verim (mamul kg / et kg); paket sayısı ve EKP bundan hesaplanır",
        "algorithm": algorithm,
        "cv_mae": cv,
        "features": feature_names(PRODUCTION_NUMERIC, full_categories),
        "rows": {"train": split, "test": len(rows) - split},
        "baseline": f"Eğitim verisindeki ortalama et bazlı verim (%{baseline_yield * 100:.2f})",
        "test": {
            "baseline": baseline_metrics,
            "model": model_metrics,
            "improvement_pct": {
                k: _improvement(baseline_metrics[k], model_metrics[k]) for k in model_metrics
            },
        },
        "samples": samples,
    }
    return bundle, meta


# --- Model B ---


def cutting_rows(rows: list[dict]) -> tuple[list[CuttingFeatures], np.ndarray]:
    features = [
        CuttingFeatures(
            species=r["species"],
            supplier=r["supplier"],
            input_kg=float(r["input_kg"]),
            month=date.fromisoformat(r["cut_date"]).month,
        )
        for r in rows
    ]
    shares = np.array([[float(r[f"{p}_kg"]) / float(r["input_kg"]) for p in data_gen.PARTS] for r in rows])
    return features, shares


def normalize_shares(predicted: np.ndarray) -> np.ndarray:
    clipped = np.clip(predicted, 0.001, None)
    return clipped / clipped.sum(axis=-1, keepdims=True)


def train_model_b(rows: list[dict]) -> tuple[dict, dict]:
    features, shares = cutting_rows(rows)
    split = int(len(rows) * (1 - TEST_SHARE))
    categories = categories_of(features[:split], CUTTING_CATEGORICAL)
    x_train = cutting_matrix(features[:split], categories)
    x_test = cutting_matrix(features[split:], categories)
    algorithm, cv = _select(candidates(True), x_train, shares[:split])
    model = candidates(True)[algorithm].fit(x_train, shares[:split])

    weights = np.array([f.input_kg for f in features[split:]])[:, None]
    actual_kg = shares[split:] * weights
    baseline_kg = np.array([STANDARD_SHARES[p] for p in data_gen.PARTS])[None, :] * weights
    model_kg = normalize_shares(model.predict(x_test)) * weights

    def evaluate(predicted: np.ndarray) -> dict[str, Any]:
        return {
            "mae_kg": round(_mae(predicted - actual_kg), 4),
            "mape_pct": round(_mape(actual_kg.ravel(), predicted.ravel()), 3),
            "mae_kg_by_part": {
                p: round(_mae(predicted[:, i] - actual_kg[:, i]), 4) for i, p in enumerate(data_gen.PARTS)
            },
        }

    baseline_metrics = evaluate(baseline_kg)
    model_metrics = evaluate(model_kg)
    test_rows = rows[split:]
    samples = [
        {
            "cutting_no": test_rows[i]["cutting_no"],
            "species": test_rows[i]["species"],
            "supplier": test_rows[i]["supplier"],
            "input_kg": float(test_rows[i]["input_kg"]),
            "parts": [
                {
                    "part": p,
                    "actual_kg": round(float(actual_kg[i, j]), 2),
                    "baseline_kg": round(float(baseline_kg[i, j]), 2),
                    "model_kg": round(float(model_kg[i, j]), 2),
                }
                for j, p in enumerate(data_gen.PARTS)
            ],
        }
        for i in range(len(test_rows) - 3, len(test_rows))
    ]

    full_categories = categories_of(features, CUTTING_CATEGORICAL)
    final = candidates(True)[algorithm].fit(cutting_matrix(features, full_categories), shares)
    bundle = {
        "model": final,
        "categories": full_categories,
        "algorithm": algorithm,
        "version": f"B-{VERSION}",
        "parts": list(data_gen.PARTS),
    }
    meta = {
        "version": bundle["version"],
        "target": "Parça payları (but, sırt, omuz, kaburga, kıyma, fire); toplamı 1'e ölçeklenir, × giriş kg",
        "algorithm": algorithm,
        "cv_mae": cv,
        "features": feature_names(CUTTING_NUMERIC, full_categories),
        "rows": {"train": split, "test": len(rows) - split},
        "baseline": "Reçetedeki standart oran × giriş ağırlığı (KUZU-STD)",
        "test": {
            "baseline": baseline_metrics,
            "model": model_metrics,
            "improvement_pct": {
                k: _improvement(baseline_metrics[k], model_metrics[k]) for k in ("mae_kg", "mape_pct")
            },
        },
        "samples": samples,
    }
    return bundle, meta


LIMITATIONS = [
    "Veri sentetiktir: etkiler data_gen.py'de bizim yazdığımız varsayımlardır. Ölçülen başarı, gerçek "
    "işletmede aynı başarının kanıtı değildir; model, varsayılan etkileri ne kadar geri "
    "bulabildiğini gösterir.",
    "Eğitim verisi küçüktür (240 üretim, 300 parçalama); yeni bir dış üretici ya da tedarikçi eğitimde "
    "görülmemişse model onu ortalama gibi değerlendirir.",
    "Gözlenmeyen etkenler (etin yağ oranı, makine ayarı, işçilik) gürültü olarak kalır; bu yüzden hata "
    "sıfıra inmez.",
    "Tahmin yalnız planlama ve sapma takibi içindir. İzleme ve geri çağırma hiçbir yerde tahmin kullanmaz; "
    "yalnız kayıtlara dayanır (CON-003).",
    "Gerçek emirler biriktikçe aynı kodla yeniden eğitilmeli ve referans yöntemle tekrar "
    "karşılaştırılmalıdır.",
]


def main() -> None:
    production = data_gen.read_csv(data_gen.OUT_DIR / "production_history.csv")
    cuttings = data_gen.read_csv(data_gen.OUT_DIR / "cutting_history.csv")
    bundle_a, meta_a = train_model_a(production)
    bundle_b, meta_b = train_model_b(cuttings)
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    joblib.dump(bundle_a, MODELS_DIR / "model_a.joblib")
    joblib.dump(bundle_b, MODELS_DIR / "model_b.joblib")
    metadata = {
        "trained_at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "seed": data_gen.SEED,
        "data": {
            "production_rows": len(production),
            "cutting_rows": len(cuttings),
            "period": f"{production[0]['order_date']} – {production[-1]['order_date']}",
            "source": "data/synthetic/ (avatar_ml.data_gen, sabit tohum)",
        },
        "split": "Kronolojik: ilk %80 eğitim, son %20 test; model seçimi eğitim kısmında 5 katlı "
        "zaman sıralı çapraz doğrulama. Sunulan model aynı yöntemle bütün veride yeniden eğitildi.",
        "model_a": meta_a,
        "model_b": meta_b,
        "limitations": LIMITATIONS,
    }
    (MODELS_DIR / "metadata.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", "utf-8"
    )
    print(json.dumps({"model_a": meta_a["test"], "model_b": meta_b["test"]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
