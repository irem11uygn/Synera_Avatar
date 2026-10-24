"""Yuvarlama kuralları — tek yer (ADR-006). Ticari yuvarlama: yarım yukarı."""

from decimal import ROUND_HALF_UP, Decimal

CENT = Decimal("0.01")
GRAM = Decimal("0.001")
UNIT_COST_STEP = Decimal("0.000001")
PERCENT_STEP = Decimal("0.01")


def round_money(amount: Decimal) -> Decimal:
    return amount.quantize(CENT, rounding=ROUND_HALF_UP)


def round_qty(qty: Decimal) -> Decimal:
    return qty.quantize(GRAM, rounding=ROUND_HALF_UP)


def round_unit_cost(cost: Decimal) -> Decimal:
    return cost.quantize(UNIT_COST_STEP, rounding=ROUND_HALF_UP)


def round_percent(percent: Decimal) -> Decimal:
    return percent.quantize(PERCENT_STEP, rounding=ROUND_HALF_UP)


def is_cent_exact(amount: Decimal) -> bool:
    return amount == round_money(amount)
