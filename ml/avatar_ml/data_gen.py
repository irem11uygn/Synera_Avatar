"""Sabit tohumlu sentetik geçmiş veri (T-18, FR-505, ADR-005).

Gerçek işletme verisi yok; bu üretici iki geçmiş üretir ve her etkiyi burada açıkça yazar:

Dış üretim emirleri (Model A): et bazlı verim = mamul kg / et kg.
    taban 0,862
    + dış üretici etkisi (FSN-01: 0, FSN-02: −0,020, FSN-03: +0,012)
    + et tedarikçisi etkisi (TED-ET: 0, TED-ET-2: −0,015, TED-ET-3: +0,006)
    − yaz kuruması (Temmuz'da en çok 0,010; mevsimsel kosinüs, Ocak'ta 0)
    − etin bekleme süresi (2 günden sonraki her gün 0,004)
    − küçük parti kaybı (1,2 / et kg; 100 kg'da 0,012)
    + gözlenmeyen değişkenlik (yağ oranı, makine ayarı…): N(0; 0,010)
    Senaryo koşulu (FSN-01, TED-ET, 100 kg, taze et, Ekim) ≈ 0,850 → 85 paket.

Parçalamalar (Model B): parça payları (but, sırt, omuz, kaburga, kıyma, fire).
    tür tabanı (kuzu = reçetedeki standart oranlar 0,27 / 0,17 / 0,20 / 0,12 / 0,12 / 0,12)
    + ağırlık etkisi: türün ortalamasından ağır karkasta but ve sırt payı düşer, kıyma ve fire artar
    + tedarikçi etkisi (TED-KUZU-2: fire +0,010, but −0,010)
    + bahar kuzusu (Mart–Haziran) daha az yağlı: fire −0,010, but +0,010
    + gözlenmeyen değişkenlik: her pay × exp(N(0; 0,04)), sonra toplam 1'e ölçeklenir.

Aynı tohum her çalıştırmada aynı veriyi üretir. Çalıştırma: python -m avatar_ml.data_gen
"""

import csv
import math
from datetime import date, timedelta
from pathlib import Path

import numpy as np

SEED = 2026
START = date(2024, 11, 1)
DAYS = 720
OUT_DIR = Path(__file__).resolve().parents[2] / "data" / "synthetic"

SUBCONTRACTORS = {"FSN-01": 0.0, "FSN-02": -0.020, "FSN-03": 0.012}
MEAT_SUPPLIERS = {"TED-ET": 0.0, "TED-ET-2": -0.015, "TED-ET-3": 0.006}
PRICES = {"BAHARAT": 24.00, "BAGIRSAK": 11.60}
SERVICE_UNIT_PRICE = 5.50
PACKAGE_KG = 1.0

PARTS = ("KUZU-BUT", "KUZU-SIRT", "KUZU-OMUZ", "KUZU-KABURGA", "KUZU-KIYMA", "FIRE")
SPECIES_BASE = {
    "KUZU": (0.27, 0.17, 0.20, 0.12, 0.12, 0.12),
    "KOYUN": (0.25, 0.16, 0.21, 0.13, 0.14, 0.11),
    "KECI": (0.26, 0.15, 0.20, 0.13, 0.11, 0.15),
}
SPECIES_KG = {"KUZU": (16.0, 32.0), "KOYUN": (25.0, 45.0), "KECI": (14.0, 28.0)}
WEIGHT_EFFECT = (-0.030, -0.010, 0.000, 0.000, 0.020, 0.020)  # ağırlık sapması (oran) başına
CARCASS_SUPPLIERS = {"TED-KUZU": 0.0, "TED-KUZU-2": 1.0}

PRODUCTION_COLUMNS = (
    "order_no",
    "order_date",
    "subcontractor",
    "meat_supplier",
    "meat_kg",
    "spice_kg",
    "casing_kg",
    "meat_age_days",
    "meat_unit_price",
    "raw_material_cost",
    "service_unit_price",
    "output_kg",
    "packages",
    "yield_main",
    "ekp",
)
CUTTING_COLUMNS = ("cutting_no", "cut_date", "species", "supplier", "input_kg", *(f"{p}_kg" for p in PARTS))


def _dates(rng: np.random.Generator, n: int) -> list[date]:
    return sorted(START + timedelta(days=int(d)) for d in rng.integers(0, DAYS, size=n))


def summer_drying(month: int) -> float:
    """Temmuz'da 1, Ocak'ta 0 olan mevsimsel etki."""
    return max(0.0, math.cos(2 * math.pi * (month - 7) / 12))


def production_history(n: int = 240, seed: int = SEED) -> list[dict]:
    rng = np.random.default_rng(seed)
    rows = []
    for i, day in enumerate(_dates(rng, n), start=1):
        subcontractor = str(rng.choice(list(SUBCONTRACTORS), p=[0.5, 0.3, 0.2]))
        supplier = str(rng.choice(list(MEAT_SUPPLIERS), p=[0.55, 0.3, 0.15]))
        meat_kg = float(round(rng.uniform(60, 220) / 5) * 5)
        spice_kg = round(meat_kg * float(np.clip(rng.normal(0.020, 0.002), 0.014, 0.026)), 2)
        casing_kg = round(meat_kg * float(np.clip(rng.normal(0.050, 0.005), 0.035, 0.065)), 2)
        age = int(rng.integers(0, 8))
        yield_main = (
            0.862
            + SUBCONTRACTORS[subcontractor]
            + MEAT_SUPPLIERS[supplier]
            - 0.010 * summer_drying(day.month)
            - 0.004 * max(0, age - 2)
            - 1.2 / meat_kg
            + rng.normal(0, 0.010)
        )
        yield_main = float(np.clip(yield_main, 0.70, 0.95))
        output_kg = round(meat_kg * yield_main, 2)
        packages = int(output_kg // PACKAGE_KG)
        meat_price = round(float(rng.normal(9.70, 0.40)), 2)
        raw = round(meat_kg * meat_price + spice_kg * PRICES["BAHARAT"] + casing_kg * PRICES["BAGIRSAK"], 2)
        ekp = (raw + SERVICE_UNIT_PRICE * packages) / packages
        rows.append(
            {
                "order_no": f"SYN-URT-{i:04d}",
                "order_date": day.isoformat(),
                "subcontractor": subcontractor,
                "meat_supplier": supplier,
                "meat_kg": meat_kg,
                "spice_kg": spice_kg,
                "casing_kg": casing_kg,
                "meat_age_days": age,
                "meat_unit_price": meat_price,
                "raw_material_cost": raw,
                "service_unit_price": SERVICE_UNIT_PRICE,
                "output_kg": output_kg,
                "packages": packages,
                "yield_main": round(packages * PACKAGE_KG / meat_kg, 4),
                "ekp": round(ekp, 4),
            }
        )
    return rows


def cutting_history(n: int = 300, seed: int = SEED + 1) -> list[dict]:
    rng = np.random.default_rng(seed)
    rows = []
    for i, day in enumerate(_dates(rng, n), start=1):
        species = str(rng.choice(list(SPECIES_BASE), p=[0.75, 0.15, 0.10]))
        supplier = str(rng.choice(list(CARCASS_SUPPLIERS), p=[0.65, 0.35]))
        low, high = SPECIES_KG[species]
        input_kg = round(float(rng.uniform(low, high)), 2)
        mean_kg = (low + high) / 2
        deviation = (input_kg - mean_kg) / mean_kg
        shares = np.array(SPECIES_BASE[species]) + np.array(WEIGHT_EFFECT) * deviation
        if CARCASS_SUPPLIERS[supplier]:
            shares += np.array((-0.010, 0, 0, 0, 0, 0.010))
        if 3 <= day.month <= 6:
            shares += np.array((0.010, 0, 0, 0, 0, -0.010))
        shares = np.clip(shares, 0.01, None) * np.exp(rng.normal(0, 0.04, size=len(PARTS)))
        shares = shares / shares.sum()
        kgs = np.round(shares * input_kg, 2)
        kgs[-1] = round(input_kg - float(kgs[:-1].sum()), 2)  # tartı dengesi: parçalar + fire = giriş
        rows.append(
            {
                "cutting_no": f"SYN-PRC-{i:04d}",
                "cut_date": day.isoformat(),
                "species": species,
                "supplier": supplier,
                "input_kg": input_kg,
                **{f"{part}_kg": float(kg) for part, kg in zip(PARTS, kgs, strict=True)},
            }
        )
    return rows


def write_csv(path: Path, columns: tuple[str, ...], rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def read_csv(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def main() -> None:
    write_csv(OUT_DIR / "production_history.csv", PRODUCTION_COLUMNS, production_history())
    write_csv(OUT_DIR / "cutting_history.csv", CUTTING_COLUMNS, cutting_history())
    print(f"Sentetik veri yazıldı: {OUT_DIR}")


if __name__ == "__main__":
    main()
