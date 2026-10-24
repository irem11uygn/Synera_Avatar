"""Parçalama maliyet dağıtımı (AT-03, FR-206)."""

import random
from decimal import Decimal as D

import pytest

from app.domain.allocation import CuttingLine, allocate, allocate_cutting_cost
from app.errors import InvalidInput
from app.models.enums import AllocationMethod, RecipeLineType

PARTS = [  # project_analysis.md §3.3 örneği: 22 kg parça + 3 kg fire, toplam maliyet 351,00 €
    ("but", D("7"), D("22")),
    ("sirt", D("4"), D("26")),
    ("omuz", D("5"), D("18")),
    ("kaburga", D("3"), D("14")),
    ("kiyma", D("3"), D("16")),
]


def lamb_lines() -> list[CuttingLine]:
    lines = [CuttingLine(key, RecipeLineType.PARCA, kg, price, True) for key, kg, price in PARTS]
    return [*lines, CuttingLine("fire", RecipeLineType.FIRE, D("3"), None, False)]


def test_at03_quantity_weighted_allocation():
    shares = allocate_cutting_cost(D("351.00"), lamb_lines(), AllocationMethod.MIKTAR)
    assert shares == {
        "but": D("111.68"),
        "sirt": D("63.82"),
        "omuz": D("79.77"),
        "kaburga": D("47.87"),  # eşit kalanda reçete sırası: kaburga kıymadan önce
        "kiyma": D("47.86"),
        "fire": D("0.00"),
    }
    assert sum(shares.values()) == D("351.00")


def test_at03_value_weighted_allocation():
    shares = allocate_cutting_cost(D("351.00"), lamb_lines(), AllocationMethod.DEGER)
    assert shares == {
        "but": D("123.41"),
        "sirt": D("83.34"),
        "omuz": D("72.12"),
        "kaburga": D("33.66"),
        "kiyma": D("38.47"),
        "fire": D("0.00"),
    }
    assert sum(shares.values()) == D("351.00")


def test_naive_rounding_would_lose_a_cent():
    """Neden en büyük kalan yöntemi: düz yuvarlama miktar ağırlıklı örnekte 350,99 verir."""
    naive = sum((D("351.00") * kg / D("22")).quantize(D("0.01")) for _, kg, _ in PARTS)
    assert naive == D("350.99")


def test_line_that_bears_no_cost_gets_zero():
    lines = [*lamb_lines(), CuttingLine("kemik", RecipeLineType.YAN_URUN, D("1"), D("2"), False)]
    assert allocate_cutting_cost(D("351.00"), lines, AllocationMethod.MIKTAR)["kemik"] == D("0.00")


def test_value_method_requires_value_per_kg():
    lines = [CuttingLine("but", RecipeLineType.PARCA, D("7"), None, True)]
    with pytest.raises(InvalidInput, match="€/kg"):
        allocate_cutting_cost(D("100.00"), lines, AllocationMethod.DEGER)


def test_cost_without_any_bearing_line_is_rejected():
    with pytest.raises(InvalidInput, match="taşıyacak satır yok"):
        allocate(D("10.00"), [("fire", D("0"))])


def test_total_must_be_cent_exact_and_weights_non_negative():
    with pytest.raises(InvalidInput):
        allocate(D("10.005"), [("a", D("1"))])
    with pytest.raises(InvalidInput):
        allocate(D("10.00"), [("a", D("-1")), ("b", D("2"))])


def test_shares_always_add_up_and_stay_within_a_cent_of_exact():
    """Rastgele 500 durum (sabit tohum): toplam her zaman korunur, hiçbir pay 1 kuruştan fazla sapmaz."""
    rng = random.Random(2026)
    for _ in range(500):
        total = D(rng.randint(0, 1_000_000)) / 100
        weights = [(i, D(rng.randint(1, 5000)) / 100) for i in range(rng.randint(1, 8))]
        shares = allocate(total, weights)
        weight_sum = sum(w for _, w in weights)
        assert sum(shares.values()) == total
        for key, weight in weights:
            assert abs(shares[key] - total * weight / weight_sum) < D("0.01")
