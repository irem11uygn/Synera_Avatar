"""Dış üretim emri — Görev 1 (api.md §4.1)."""

from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter
from pydantic import BaseModel, Field
from sqlalchemy import select

from app.api.deps import Db, ProductionUser, WebUser
from app.api.fields import UtcDateTime
from app.domain.money import round_money, tr_number
from app.errors import NotFound
from app.models import ProductionOrder
from app.models.enums import BaseUnit, ForecastTarget, ProductionKind, ProductionStatus, Severity
from app.services import alarms, audit, production
from app.services.ai import first_forecast
from app.services.lookups import get_or_404, lot_by_no

router = APIRouter(prefix="/production-orders", tags=["dış üretim"])

PositiveQty = Annotated[Decimal, Field(gt=0, max_digits=12, decimal_places=3)]
NonNegativeQty = Annotated[Decimal, Field(ge=0, max_digits=12, decimal_places=3)]


class PlannedInputIn(BaseModel):
    lot_no: str
    qty: PositiveQty


class OrderIn(BaseModel):
    subcontractor_id: int
    output_product_id: int
    planned_qty: PositiveQty
    service_unit_price: Decimal | None = Field(default=None, ge=0, max_digits=14, decimal_places=4)
    inputs: list[PlannedInputIn] = Field(min_length=1)


class InputResultIn(BaseModel):
    lot_no: str
    consumed_qty: NonNegativeQty
    returned_qty: NonNegativeQty = Decimal(0)


class CompleteIn(BaseModel):
    received_qty: PositiveQty
    inputs: list[InputResultIn] = Field(min_length=1)
    service_amount: Decimal | None = Field(default=None, ge=0, max_digits=14, decimal_places=2)
    service_invoice_no: str | None = Field(default=None, max_length=50)
    service_note: str | None = Field(default=None, max_length=500)
    output_lot_no: str | None = Field(default=None, max_length=40)


class InputOut(BaseModel):
    lot_no: str
    product_name: str
    base_unit: BaseUnit
    planned_qty: Decimal
    shipped_qty: Decimal
    consumed_qty: Decimal
    returned_qty: Decimal
    consumed_value: Decimal


class CostOut(BaseModel):
    raw_materials: Decimal
    service: Decimal
    total: Decimal
    ekp: Decimal
    ekp_display: Decimal


class SalesOut(BaseModel):
    vkp: Decimal
    gross_profit_per_unit: Decimal
    margin_pct: Decimal


class YieldOut(BaseModel):
    output_kg: Decimal
    inputs_kg: Decimal
    main_input_kg: Decimal
    yield_total_pct: Decimal
    yield_main_pct: Decimal


class ForecastOut(BaseModel):
    """Model A: emir açılırken kaydedilen tahmin; kabulden sonra gerçekle sapma (FR-502)."""

    model_version: str
    created_at: UtcDateTime
    expected_qty: Decimal
    yield_main_pct: Decimal
    ekp: Decimal
    baseline_qty: Decimal
    baseline_ekp: Decimal
    qty_deviation: Decimal | None  # gerçek − tahmin
    ekp_deviation: Decimal | None  # gerçek EKP − tahmini EKP
    baseline_qty_deviation: Decimal | None


class OrderOut(BaseModel):
    id: int
    order_no: str
    status: ProductionStatus
    subcontractor_id: int
    subcontractor_name: str
    output_product_id: int
    output_product_name: str
    base_unit: BaseUnit
    planned_qty: Decimal
    received_qty: Decimal | None
    quantity_difference: Decimal | None  # teslim alınan − planlanan (FR-109)
    service_unit_price: Decimal | None
    service_amount: Decimal | None
    service_invoice_no: str | None
    service_note: str | None
    output_lot_no: str | None
    ordered_at: UtcDateTime
    shipped_at: UtcDateTime | None
    completed_at: UtcDateTime | None
    inputs: list[InputOut]
    cost: CostOut | None
    sales: SalesOut | None
    yield_: YieldOut | None = Field(serialization_alias="yield")
    forecast: ForecastOut | None


def _forecast_out(db: Db, order: ProductionOrder, actual_ekp: Decimal | None) -> ForecastOut | None:
    record = first_forecast(db, ForecastTarget.URETIM_EMRI, order.id)
    if record is None:
        return None
    p = {key: Decimal(value) for key, value in record.prediction.items()}
    received = order.received_qty
    return ForecastOut(
        model_version=record.model_version,
        created_at=record.created_at,
        expected_qty=p["expected_qty"],
        yield_main_pct=p["yield_main_pct"],
        ekp=round_money(p["ekp"]),
        baseline_qty=p["baseline_qty"],
        baseline_ekp=round_money(p["baseline_ekp"]),
        qty_deviation=received - p["expected_qty"] if received is not None else None,
        ekp_deviation=round_money(actual_ekp - p["ekp"]) if actual_ekp is not None else None,
        baseline_qty_deviation=received - p["baseline_qty"] if received is not None else None,
    )


def _order_out(db: Db, order: ProductionOrder) -> OrderOut:
    s = production.order_summary(db, order)
    return OrderOut(
        id=order.id,
        order_no=order.order_no,
        status=order.status,
        subcontractor_id=s.subcontractor.id,
        subcontractor_name=s.subcontractor.name,
        output_product_id=s.product.id,
        output_product_name=s.product.name,
        base_unit=s.product.base_unit,
        planned_qty=order.planned_qty,
        received_qty=order.received_qty,
        quantity_difference=order.received_qty - order.planned_qty
        if order.received_qty is not None
        else None,
        service_unit_price=order.service_unit_price,
        service_amount=order.service_amount,
        service_invoice_no=order.service_invoice_no,
        service_note=order.service_note,
        output_lot_no=s.output_lot_no,
        ordered_at=order.ordered_at,
        shipped_at=order.shipped_at,
        completed_at=order.completed_at,
        inputs=[InputOut(**vars(line)) for line in s.inputs],
        cost=CostOut(**vars(s.cost), ekp_display=s.cost.ekp_display) if s.cost else None,
        sales=SalesOut(vkp=s.product.sale_price, **vars(s.sales))
        if s.sales and s.product.sale_price
        else None,
        yield_=YieldOut(**vars(s.yield_)) if s.yield_ else None,
        forecast=_forecast_out(db, order, s.cost.ekp if s.cost else None),
    )


@router.post("", response_model=OrderOut, response_model_by_alias=True, status_code=201)
def create(body: OrderIn, db: Db, user: ProductionUser) -> OrderOut:
    order = production.create_order(
        db,
        subcontractor_id=body.subcontractor_id,
        output_product_id=body.output_product_id,
        planned_qty=body.planned_qty,
        service_unit_price=body.service_unit_price,
        inputs=[production.PlannedInput(lot_by_no(db, i.lot_no).id, i.qty) for i in body.inputs],
        user_id=user.id,
    )
    audit.log(
        db,
        "URETIM_EMRI",
        f"Dış üretim emri {order.order_no} açıldı ({tr_number(order.planned_qty)} planlanan)",
        user=user,
        ref_type="PRODUCTION_ORDER",
        ref_id=order.id,
    )
    return _order_out(db, order)


@router.get("", response_model=list[OrderOut], response_model_by_alias=True)
def list_orders(db: Db, _: WebUser) -> list[OrderOut]:
    orders = db.scalars(
        select(ProductionOrder)
        .where(ProductionOrder.kind == ProductionKind.DIS_URETIM)
        .order_by(ProductionOrder.id.desc())
    )
    return [_order_out(db, order) for order in orders]


@router.get("/{order_id}", response_model=OrderOut, response_model_by_alias=True)
def get_order(order_id: int, db: Db, _: WebUser) -> OrderOut:
    order = get_or_404(db, ProductionOrder, order_id, "Üretim emri")
    if order.kind != ProductionKind.DIS_URETIM:
        raise NotFound("Dış üretim emri bulunamadı (bu kayıt bir yeniden işleme).", id=order_id)
    return _order_out(db, order)


@router.post("/{order_id}/ship", response_model=OrderOut, response_model_by_alias=True)
def ship(order_id: int, db: Db, user: ProductionUser) -> OrderOut:
    order = production.ship_order(db, order_id, user_id=user.id)
    audit.log(
        db,
        "URETIM_SEVK",
        f"{order.order_no}: hammadde dış üreticiye sevk edildi",
        user=user,
        ref_type="PRODUCTION_ORDER",
        ref_id=order.id,
    )
    return _order_out(db, order)


@router.post("/{order_id}/complete", response_model=OrderOut, response_model_by_alias=True)
def complete(order_id: int, body: CompleteIn, db: Db, user: ProductionUser) -> OrderOut:
    order = production.complete_order(
        db,
        order_id,
        received_qty=body.received_qty,
        inputs=[
            production.InputResult(lot_by_no(db, i.lot_no).id, i.consumed_qty, i.returned_qty)
            for i in body.inputs
        ],
        service_amount=body.service_amount,
        service_invoice_no=body.service_invoice_no,
        service_note=body.service_note,
        output_lot_no=body.output_lot_no,
        user_id=user.id,
    )
    out = _order_out(db, order)
    audit.log(
        db,
        "URETIM_TAMAM",
        f"{order.order_no} tamamlandı: {tr_number(order.received_qty or 0)} teslim alındı",
        user=user,
        ref_type="PRODUCTION_ORDER",
        ref_id=order.id,
    )
    alarms.run_rules(db, user)  # verim sapması hemen görünsün
    return out


class CancelIn(BaseModel):
    note: str | None = Field(default=None, max_length=255)  # sevk edilmiş emirde zorunlu: neden iptal


@router.post("/{order_id}/cancel", response_model=OrderOut, response_model_by_alias=True)
def cancel(order_id: int, db: Db, user: ProductionUser, body: CancelIn | None = None) -> OrderOut:
    """Taslak emir iptal edilir; sevk edilmiş emirde gönderilen hammadde ana depoya iade edilir."""
    note = body.note if body is not None else None
    order = production.cancel_order(db, order_id, note=note, user_id=user.id)
    audit.log(
        db,
        "URETIM_IPTAL",
        f"{order.order_no} iptal edildi" + (f": {note}" if note else ""),
        user=user,
        severity=Severity.UYARI,
        ref_type="PRODUCTION_ORDER",
        ref_id=order.id,
    )
    return _order_out(db, order)
