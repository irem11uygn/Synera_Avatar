"""Ana sayfa grafikleri: gerçek kayıtlardan; model tahmini kayıtlı tahminden (ai_forecasts).

- Üretim geçmişi: tamamlanmış dış üretim emirlerinin gerçek EKP'si ve emir açılırken kaydedilmiş model
  tahmini. Sistemde az emir varken grafik boş kalmasın diye modelin test verisi (sentetik geçmiş, eğitimde
  görülmemiş emirler) ayrı seri olarak verilir; arayüz bunu açıkça "sentetik" diye etiketler.
- Hedef/gerçekleşen: son 30 günde tamamlanan emirlerin planlanan ve teslim alınan miktarı.
- Maliyet dağılımı: son tamamlanan emrin hammadde kalemleri ve hizmet bedeli (EKP'yi oluşturanlar).
- Parça maliyetleri: son onaylanan parçalamada parça başına €/kg.
- Sevkiyat: son 30 günde müşteri başına satılan miktar ve tutar.
"""

from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal

from avatar_ml import predict
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.domain.clock import business_today
from app.domain.money import round_money, round_percent
from app.models import AiForecast, Cutting, CuttingOutput, Partner, Product, ProductionOrder, Sale, SaleLine
from app.models.enums import BaseUnit, CuttingStatus, ForecastTarget, ProductionStatus, RecipeLineType
from app.models.types import utcnow
from app.services.production import order_summary

WINDOW_DAYS = 30
HISTORY_POINTS = 12
SYNTHETIC_POINTS = 24


@dataclass(frozen=True)
class EkpPoint:
    label: str  # emir no
    day: date
    actual: Decimal
    forecast: Decimal | None


@dataclass(frozen=True)
class Slice:
    label: str
    value: Decimal


@dataclass(frozen=True)
class PartCost:
    label: str
    kg: Decimal
    unit_cost: Decimal


@dataclass(frozen=True)
class Shipment:
    customer: str
    qty_by_unit: dict[str, Decimal]
    amount: Decimal


@dataclass(frozen=True)
class Charts:
    ekp_history: list[EkpPoint]
    ekp_synthetic: list[EkpPoint]
    target_qty: Decimal
    actual_qty: Decimal
    target_label: str
    cost_order_no: str | None
    cost_slices: list[Slice]
    cost_ekp: Decimal | None
    parts_cutting_no: str | None
    part_costs: list[PartCost]
    shipments: list[Shipment]


def charts(session: Session) -> Charts:
    orders = session.scalars(
        select(ProductionOrder)
        .where(ProductionOrder.status == ProductionStatus.TAMAMLANDI)
        .order_by(ProductionOrder.completed_at.desc(), ProductionOrder.id.desc())
        .limit(HISTORY_POINTS)
    ).all()
    forecasts = {
        f.target_id: f.prediction
        for f in session.scalars(
            select(AiForecast).where(AiForecast.target_type == ForecastTarget.URETIM_EMRI)
        )
    }
    history: list[EkpPoint] = []
    summaries = {}
    for order in orders:
        summary = order_summary(session, order)
        summaries[order.id] = summary
        if summary.cost is None:
            continue
        predicted = forecasts.get(order.id, {}).get("ekp")
        history.append(
            EkpPoint(
                label=order.order_no,
                day=business_today(order.completed_at or order.ordered_at),
                actual=summary.cost.ekp_display,
                forecast=round_money(Decimal(predicted)) if predicted else None,
            )
        )
    history.reverse()  # eskiden yeniye

    since = utcnow() - timedelta(days=WINDOW_DAYS)
    recent = [o for o in orders if o.completed_at and o.completed_at >= since]
    target = sum((o.planned_qty for o in recent), Decimal(0))
    actual = sum((o.received_qty or Decimal(0) for o in recent), Decimal(0))

    slices: list[Slice] = []
    cost_order_no = cost_ekp = None
    latest = next((summaries[o.id] for o in orders if summaries[o.id].cost is not None), None)
    if latest is not None and latest.cost is not None:
        cost_order_no, cost_ekp = latest.order.order_no, latest.cost.ekp_display
        slices = [
            Slice(line.product_name, line.consumed_value) for line in latest.inputs if line.consumed_value
        ]
        slices.append(Slice("Dış üretim hizmeti", latest.cost.service))

    cutting = session.scalars(
        select(Cutting).where(Cutting.status == CuttingStatus.ONAYLANDI).order_by(Cutting.approved_at.desc())
    ).first()
    parts: list[PartCost] = []
    if cutting is not None:
        rows = session.execute(
            select(Product.name, CuttingOutput.actual_qty, CuttingOutput.allocated_cost)
            .join(Product, Product.id == CuttingOutput.product_id)
            .where(
                CuttingOutput.cutting_id == cutting.id,
                CuttingOutput.line_type != RecipeLineType.FIRE,
                CuttingOutput.actual_qty > 0,
            )
            .order_by(CuttingOutput.id)
        ).all()
        parts = [
            PartCost(name, kg, round_money(cost / kg)) for name, kg, cost in rows if kg and cost is not None
        ]

    sold = session.execute(
        select(Partner.name, Product.base_unit, func.sum(SaleLine.qty), func.sum(SaleLine.amount))
        .join(Sale, Sale.id == SaleLine.sale_id)
        .join(Partner, Partner.id == Sale.customer_id)
        .join(Product, Product.id == SaleLine.product_id)
        .where(Sale.sold_at >= since)
        .group_by(Partner.name, Product.base_unit)
    ).all()
    by_customer: dict[str, tuple[dict[str, Decimal], Decimal]] = {}
    for name, unit, qty, amount in sold:
        units, total = by_customer.get(name, ({}, Decimal(0)))
        units["adet" if unit == BaseUnit.ADET else "kg"] = qty
        by_customer[name] = (units, total + amount)
    shipments = sorted(
        (Shipment(name, units, total) for name, (units, total) in by_customer.items()),
        key=lambda s: -s.amount,
    )[:8]

    return Charts(
        ekp_history=history,
        ekp_synthetic=_synthetic(),
        target_qty=target,
        actual_qty=actual,
        target_label=f"Son {WINDOW_DAYS} gün: planlanan / teslim alınan",
        cost_order_no=cost_order_no,
        cost_slices=slices,
        cost_ekp=cost_ekp,
        parts_cutting_no=cutting.cutting_no if cutting else None,
        part_costs=parts,
        shipments=shipments,
    )


def _synthetic() -> list[EkpPoint]:
    """Model A'nın test verisi: gerçek EKP ve modelin tahmini (eğitimde görülmemiş emirler)."""
    try:
        samples = predict.metadata()["model_a"]["samples"]
    except (predict.ModelUnavailable, KeyError, TypeError):
        return []
    rows = sorted(samples, key=lambda s: s["order_date"])[-SYNTHETIC_POINTS:]
    return [
        EkpPoint(
            label=row["order_no"],
            day=date.fromisoformat(row["order_date"]),
            actual=Decimal(str(row["actual_ekp"])),
            forecast=Decimal(str(row["model_ekp"])),
        )
        for row in rows
    ]


def fill_rate(target: Decimal, actual: Decimal) -> Decimal | None:
    return round_percent(actual / target * 100) if target else None
