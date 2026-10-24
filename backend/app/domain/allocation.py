"""Ortak maliyetin dağıtımı (FR-202, FR-206, AT-03)."""

from collections.abc import Hashable, Sequence
from dataclasses import dataclass
from decimal import ROUND_FLOOR, Decimal

from app.domain.money import CENT, is_cent_exact
from app.errors import InvalidInput
from app.models.enums import AllocationMethod, RecipeLineType


def allocate[K: Hashable](total: Decimal, weights: Sequence[tuple[K, Decimal]]) -> dict[K, Decimal]:
    """Toplamı ağırlıklarla orantılı, kuruşa yuvarlanmış paylara böler; paylar toplamı = toplam.

    En büyük kalan yöntemi: önce herkes aşağı yuvarlanmış payını alır, eksik kalan kuruşlar
    en büyük kesirli kalanı olan satırlara birer birer verilir. Eşitlikte sıradaki ilk satır
    öne geçer (reçete sırası).
    """
    if total < 0 or not is_cent_exact(total):
        raise InvalidInput(
            "Dağıtılacak tutar sıfır veya pozitif ve kuruş hassasiyetinde olmalı.", total=total
        )
    if any(weight < 0 for _, weight in weights):
        raise InvalidInput("Dağıtım ağırlıkları eksi olamaz.")
    weight_sum = sum((weight for _, weight in weights), Decimal(0))
    if weight_sum == 0:
        if total == 0:
            return {key: Decimal("0.00") for key, _ in weights}
        raise InvalidInput("Maliyeti taşıyacak satır yok (bütün ağırlıklar sıfır).", total=total)

    exact_cents = [total * weight / weight_sum / CENT for _, weight in weights]
    cents = [int(c.to_integral_value(rounding=ROUND_FLOOR)) for c in exact_cents]
    missing = int(total / CENT) - sum(cents)
    by_remainder = sorted(range(len(weights)), key=lambda i: (-(exact_cents[i] - cents[i]), i))
    for i in by_remainder[:missing]:
        cents[i] += 1
    return {key: Decimal(cents[i]) * CENT for i, (key, _) in enumerate(weights)}


@dataclass(frozen=True)
class CuttingLine:
    key: Hashable
    line_type: RecipeLineType
    actual_kg: Decimal
    value_per_kg: Decimal | None
    bears_cost: bool


def cutting_weight(line: CuttingLine, method: AllocationMethod) -> Decimal:
    """Ağırlık = kg × katsayı; katsayı miktar yönteminde 1, değer yönteminde €/kg. Fire hiç pay almaz."""
    if line.line_type == RecipeLineType.FIRE or not line.bears_cost:
        return Decimal(0)
    if method == AllocationMethod.MIKTAR:
        return line.actual_kg
    if line.value_per_kg is None:
        raise InvalidInput("Değer ağırlıklı dağıtımda her satırın €/kg değeri gerekli.", line=str(line.key))
    return line.actual_kg * line.value_per_kg


def allocate_cutting_cost(
    total_cost: Decimal, lines: Sequence[CuttingLine], method: AllocationMethod
) -> dict[Hashable, Decimal]:
    return allocate(total_cost, [(line.key, cutting_weight(line, method)) for line in lines])
