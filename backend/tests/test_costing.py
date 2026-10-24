"""Maliyet hesapları — şartname rakamları (AT-01, AT-02)."""

from decimal import Decimal as D

import pytest

from app.domain.costing import line_amount, outflow_value, production_cost, profitability, unit_cost
from app.errors import InsufficientStock, InvalidInput


def test_at01_narin_sucuk_ekp_is_18_16():
    """100 kg et × 9,70 + 2 kg baharat × 24,00 + 5 kg bağırsak × 11,60 + 85 × 5,50 hizmet; 85 paket."""
    raw = [line_amount(D("100"), D("9.70")), line_amount(D("2"), D("24.00")), line_amount(D("5"), D("11.60"))]
    cost = production_cost(raw, line_amount(D("85"), D("5.50")), received_qty=D("85"))

    assert raw == [D("970.00"), D("48.00"), D("58.00")]
    assert cost.raw_materials == D("1076.00")
    assert cost.service == D("467.50")
    assert cost.total == D("1543.50")
    assert cost.ekp == D("18.158824")
    assert cost.ekp_display == D("18.16")


def test_at01_rounded_ekp_must_not_be_used_to_value_the_lot():
    cost = production_cost([D("1076.00")], D("467.50"), received_qty=D("85"))
    assert cost.ekp_display * 85 == D("1543.60")  # 10 sent fazla — bu yüzden lot değeri toplamdan tutulur
    assert cost.total == D("1543.50")


def test_at02_gross_profit_and_margin_at_vkp_24_90():
    ekp = production_cost([D("1076.00")], D("467.50"), received_qty=D("85")).ekp
    result = profitability(D("24.90"), ekp)
    assert result.gross_profit_per_unit == D("6.74")
    assert result.margin_pct == D("27.07")


def test_ekp_uses_actually_received_quantity():
    """Hizmet adet başına; 84 paket gelirse hem hizmet hem EKP değişir (FR-110)."""
    cost = production_cost([D("1076.00")], line_amount(D("84"), D("5.50")), received_qty=D("84"))
    assert cost.total == D("1538.00")
    assert cost.ekp_display == D("18.31")


def test_sales_from_one_lot_add_up_exactly_to_lot_value():
    """SUC-2026-045: Market A 30, B 25, C 30 paket; son çıkış kalan değerin tamamını alır."""
    qty, value, costs = D("85"), D("1543.50"), []
    for sold in (D("30"), D("25"), D("30")):
        cost = outflow_value(qty, value, sold)
        costs.append(cost)
        qty, value = qty - sold, value - cost
    assert costs == [D("544.76"), D("453.97"), D("544.77")]
    assert sum(costs) == D("1543.50")
    assert (qty, value) == (D("0"), D("0.00"))


def test_outflow_larger_than_lot_is_rejected():
    with pytest.raises(InsufficientStock):
        outflow_value(D("10"), D("97.00"), D("10.001"))


def test_invalid_quantities_are_rejected():
    with pytest.raises(InvalidInput):
        outflow_value(D("10"), D("97.00"), D("0"))
    with pytest.raises(InvalidInput):
        unit_cost(D("10.00"), D("0"))
    with pytest.raises(InvalidInput):
        profitability(D("0"), D("18.16"))


def test_lamb_purchase_line_amount_differs_from_invoice():
    """Görev 2 notu: 25 kg × 11,50 € = 287,50 € (faturadaki 351,00 € ile farklı)."""
    assert line_amount(D("25"), D("11.50")) == D("287.50")
