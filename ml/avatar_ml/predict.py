"""Sunucunun çağırdığı tahmin fonksiyonları (TR-006). Model dosyaları ml/models/ altındadır.

Dosya yoksa ya da açılamazsa ModelUnavailable yükseltilir; sunucu bunu yakalar ve iş akışını
durdurmaz (architecture.md §6).
"""

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

import joblib

from avatar_ml.features import CuttingFeatures, ProductionFeatures, cutting_matrix, production_matrix
from avatar_ml.train import normalize_shares

MODELS_DIR = Path(__file__).resolve().parents[1] / "models"


class ModelUnavailable(RuntimeError):
    pass


@lru_cache
def _bundle(name: str) -> dict[str, Any]:
    path = MODELS_DIR / f"{name}.joblib"
    if not path.exists():
        raise ModelUnavailable(f"{path.name} bulunamadı; önce 'python -m avatar_ml.train' çalıştırılmalı.")
    return joblib.load(path)


def production_yield(features: ProductionFeatures) -> tuple[float, float, str]:
    """(model verimi, referans verim, model sürümü)."""
    bundle = _bundle("model_a")
    predicted = float(bundle["model"].predict(production_matrix([features], bundle["categories"]))[0])
    return predicted, bundle["baseline_yield"], bundle["version"]


def cutting_shares(features: CuttingFeatures) -> tuple[dict[str, float], str]:
    """(parça → pay, model sürümü); paylar toplamı 1."""
    bundle = _bundle("model_b")
    shares = normalize_shares(bundle["model"].predict(cutting_matrix([features], bundle["categories"])))[0]
    return dict(zip(bundle["parts"], (float(s) for s in shares), strict=True)), bundle["version"]


def metadata() -> dict[str, Any]:
    path = MODELS_DIR / "metadata.json"
    if not path.exists():
        raise ModelUnavailable("metadata.json bulunamadı.")
    return json.loads(path.read_text(encoding="utf-8"))
