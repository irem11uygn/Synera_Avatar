"""Parçalamada ağırlık dengesi (FR-205, AT-04)."""

from collections.abc import Iterable
from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class WeightBalance:
    input_kg: Decimal
    outputs_kg: Decimal
    tolerance_kg: Decimal

    @property
    def difference_kg(self) -> Decimal:
        """Pozitif: çıkışlarda eksik (açıklanmamış) kg; negatif: girişten fazla kg."""
        return self.input_kg - self.outputs_kg

    @property
    def ok(self) -> bool:
        return abs(self.difference_kg) <= self.tolerance_kg


def weight_balance(input_kg: Decimal, output_kgs: Iterable[Decimal], tolerance_kg: Decimal) -> WeightBalance:
    """Giriş = parçalar + yan ürünler + fire, tolerans içinde mi?"""
    return WeightBalance(input_kg=input_kg, outputs_kg=sum(output_kgs, Decimal(0)), tolerance_kg=tolerance_kg)
