"""Özellik çıkarımı: eğitimde ve sunucudaki tahminde aynı kod (eğitim/sunum farkı oluşmasın).

Yalnız emir ya da parçalama açılırken bilinen bilgiler kullanılır (gerçek sonuç sızmaz).
Kategorik değerler (dış üretici, tedarikçi, tür) eğitimde görülen listeye göre tek-sıcak kodlanır;
eğitimde görülmemiş bir değer bütün sütunlarda 0 olur (model "ortalama" davranır).
"""

import math
from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class ProductionFeatures:
    subcontractor: str
    meat_supplier: str
    meat_kg: float
    spice_kg: float
    casing_kg: float
    meat_age_days: int
    month: int


@dataclass(frozen=True)
class CuttingFeatures:
    species: str
    supplier: str
    input_kg: float
    month: int


PRODUCTION_NUMERIC = (
    "meat_kg",
    "inv_meat_kg",
    "spice_ratio",
    "casing_ratio",
    "meat_age_days",
    "month_sin",
    "month_cos",
)
PRODUCTION_CATEGORICAL = ("subcontractor", "meat_supplier")
CUTTING_NUMERIC = ("input_kg", "month_sin", "month_cos", "spring")
CUTTING_CATEGORICAL = ("species", "supplier")


def _month(month: int) -> tuple[float, float]:
    angle = 2 * math.pi * (month - 1) / 12
    return math.sin(angle), math.cos(angle)


def production_numeric(f: ProductionFeatures) -> dict[str, float]:
    sin, cos = _month(f.month)
    return {
        "meat_kg": f.meat_kg,
        "inv_meat_kg": 1.0 / f.meat_kg,
        "spice_ratio": f.spice_kg / f.meat_kg,
        "casing_ratio": f.casing_kg / f.meat_kg,
        "meat_age_days": float(f.meat_age_days),
        "month_sin": sin,
        "month_cos": cos,
    }


def cutting_numeric(f: CuttingFeatures) -> dict[str, float]:
    sin, cos = _month(f.month)
    return {"input_kg": f.input_kg, "month_sin": sin, "month_cos": cos, "spring": float(3 <= f.month <= 6)}


def categories_of(rows: list[object], names: tuple[str, ...]) -> dict[str, list[str]]:
    return {name: sorted({str(getattr(row, name)) for row in rows}) for name in names}


def encode(
    numeric: dict[str, float],
    categorical: dict[str, str],
    numeric_names: tuple[str, ...],
    categories: dict[str, list[str]],
) -> list[float]:
    vector = [numeric[name] for name in numeric_names]
    for name, values in categories.items():
        vector.extend(1.0 if categorical[name] == value else 0.0 for value in values)
    return vector


def feature_names(numeric_names: tuple[str, ...], categories: dict[str, list[str]]) -> list[str]:
    return [*numeric_names, *(f"{name}={value}" for name, values in categories.items() for value in values)]


def production_matrix(rows: list[ProductionFeatures], categories: dict[str, list[str]]) -> np.ndarray:
    return np.array(
        [
            encode(
                production_numeric(r),
                {"subcontractor": r.subcontractor, "meat_supplier": r.meat_supplier},
                PRODUCTION_NUMERIC,
                categories,
            )
            for r in rows
        ]
    )


def cutting_matrix(rows: list[CuttingFeatures], categories: dict[str, list[str]]) -> np.ndarray:
    return np.array(
        [
            encode(
                cutting_numeric(r),
                {"species": r.species, "supplier": r.supplier},
                CUTTING_NUMERIC,
                categories,
            )
            for r in rows
        ]
    )
