"""Maliyet hesapları (FR-110, FR-111; ADR-006, ADR-008)."""

from collections.abc import Iterable
from dataclasses import dataclass
from decimal import Decimal

from app.domain.money import round_money, round_percent, round_unit_cost
from app.errors import InsufficientStock, InvalidInput


def line_amount(qty: Decimal, unit_price: Decimal) -> Decimal:
    """Miktar × birim fiyat, kuruşa yuvarlanmış (ör. 25 kg × 11,50 € = 287,50 €)."""
    return round_money(qty * unit_price)


def unit_cost(value: Decimal, qty: Decimal) -> Decimal:
    if qty <= 0:
        raise InvalidInput("Birim maliyet için miktar sıfırdan büyük olmalı.", qty=qty)
    return round_unit_cost(value / qty)


def outflow_value(remaining_qty: Decimal, remaining_value: Decimal, qty_out: Decimal) -> Decimal:
    """Lottan çıkan miktarın maliyeti (pozitif tutar).

    Orantılı pay kuruşa yuvarlanır; lotu sıfırlayan çıkış kalan değerin tamamını alır.
    Böylece çıkışların toplamı lot değerine kuruşu kuruşuna eşit olur (18,16 × 85 ≠ 1.543,50 sorunu).
    """
    if qty_out <= 0:
        raise InvalidInput("Çıkış miktarı sıfırdan büyük olmalı.", qty=qty_out)
    if qty_out > remaining_qty:
        raise InsufficientStock("Lotta yeterli miktar yok.", available=remaining_qty, requested=qty_out)
    if qty_out == remaining_qty:
        return remaining_value
    return round_money(remaining_value * qty_out / remaining_qty)


@dataclass(frozen=True)
class ProductionCost:
    raw_materials: Decimal
    service: Decimal
    total: Decimal
    ekp: Decimal  # gerçek birim maliyet, 6 ondalık

    @property
    def ekp_display(self) -> Decimal:
        return round_money(self.ekp)


def production_cost(
    raw_material_values: Iterable[Decimal], service_amount: Decimal, received_qty: Decimal
) -> ProductionCost:
    """Dış üretim EKP'si = (tüketilen hammadde maliyeti + hizmet) / teslim alınan miktar (FR-110)."""
    raw = sum(raw_material_values, Decimal(0))
    total = raw + service_amount
    return ProductionCost(
        raw_materials=raw, service=service_amount, total=total, ekp=unit_cost(total, received_qty)
    )


@dataclass(frozen=True)
class Profitability:
    gross_profit_per_unit: Decimal
    margin_pct: Decimal  # brüt kâr / VKP (AS-002)


def profitability(sale_price: Decimal, ekp: Decimal) -> Profitability:
    """VKP'ye göre birim brüt kâr ve marj (FR-111)."""
    if sale_price <= 0:
        raise InvalidInput("Satış fiyatı (VKP) sıfırdan büyük olmalı.", sale_price=sale_price)
    profit = sale_price - ekp
    return Profitability(
        gross_profit_per_unit=round_money(profit), margin_pct=round_percent(profit / sale_price * 100)
    )
