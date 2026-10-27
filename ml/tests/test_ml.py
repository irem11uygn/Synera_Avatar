"""Yapay zekâ paketi: sentetik veri tekrarlanabilir, modeller referansla ölçülür, paylar toplamı 1."""

import numpy as np

from avatar_ml import data_gen, predict, train
from avatar_ml.features import CuttingFeatures, ProductionFeatures


def test_same_seed_same_data():
    assert data_gen.production_history(20) == data_gen.production_history(20)
    assert data_gen.cutting_history(20) != data_gen.cutting_history(20, seed=1)


def test_cutting_rows_balance_to_input_weight():
    for row in data_gen.cutting_history(50):
        parts = sum(row[f"{p}_kg"] for p in data_gen.PARTS)
        assert abs(parts - row["input_kg"]) < 0.011


def test_training_reports_baseline_and_model_on_the_same_test_rows():
    _, meta_a = train.train_model_a(data_gen.production_history())
    _, meta_b = train.train_model_b(data_gen.cutting_history())
    for meta in (meta_a, meta_b):
        assert meta["algorithm"] in {"Ridge", "HistGradientBoosting"}
        assert set(meta["cv_mae"]) == {"Ridge", "HistGradientBoosting"}
        assert meta["rows"]["test"] > 0
    assert meta_a["test"]["model"]["packages_mae"] < meta_a["test"]["baseline"]["packages_mae"]
    assert meta_b["test"]["model"]["mae_kg"] < meta_b["test"]["baseline"]["mae_kg"]


def test_saved_models_predict_the_scenario_sensibly():
    yield_, baseline, version = predict.production_yield(
        ProductionFeatures("FSN-01", "TED-ET", 100.0, 2.0, 5.0, 0, 10)
    )
    assert version.startswith("A-") and 0.80 < yield_ < 0.90 and 0.80 < baseline < 0.90
    shares, version = predict.cutting_shares(CuttingFeatures("KUZU", "TED-KUZU", 25.0, 10))
    assert version.startswith("B-") and set(shares) == set(data_gen.PARTS)
    assert np.isclose(sum(shares.values()), 1.0)
