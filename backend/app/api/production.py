"""Dış üretim emri — Görev 1 (api.md §4.1)."""

from datetime import datetime
from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter
from pydantic import BaseModel, Field
from sqlalchemy import select

from app.api.deps import AdminUser, Db
from app.models import ProductionOrder
from app.models.enums import BaseUnit, ProductionStatus
from app.services import production
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
    ordered_at: datetime
    shipped_at: datetime | None
    completed_at: datetime | None
    inputs: list[InputOut]
    cost: CostOut | None
    sales: SalesOut | None
    yield_: YieldOut | None = Field(serialization_alias="yield")


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
    )


@router.post("", response_model=OrderOut, response_model_by_alias=True, status_code=201)
def create(body: OrderIn, db: Db, user: AdminUser) -> OrderOut:
    order = production.create_order(
        db,
        subcontractor_id=body.subcontractor_id,
        output_product_id=body.output_product_id,
        planned_qty=body.planned_qty,
        service_unit_price=body.service_unit_price,
        inputs=[production.PlannedInput(lot_by_no(db, i.lot_no).id, i.qty) for i in body.inputs],
        user_id=user.id,
    )
    return _order_out(db, order)


@router.get("", response_model=list[OrderOut], response_model_by_alias=True)
def list_orders(db: Db, _: AdminUser) -> list[OrderOut]:
    orders = db.scalars(select(ProductionOrder).order_by(ProductionOrder.id.desc()))
    return [_order_out(db, order) for order in orders]


@router.get("/{order_id}", response_model=OrderOut, response_model_by_alias=True)
def get_order(order_id: int, db: Db, _: AdminUser) -> OrderOut:
    return _order_out(db, get_or_404(db, ProductionOrder, order_id, "Üretim emri"))


@router.post("/{order_id}/ship", response_model=OrderOut, response_model_by_alias=True)
def ship(order_id: int, db: Db, user: AdminUser) -> OrderOut:
    return _order_out(db, production.ship_order(db, order_id, user_id=user.id))


@router.post("/{order_id}/complete", response_model=OrderOut, response_model_by_alias=True)
def complete(order_id: int, body: CompleteIn, db: Db, user: AdminUser) -> OrderOut:
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
    return _order_out(db, order)


@router.post("/{order_id}/cancel", response_model=OrderOut, response_model_by_alias=True)
def cancel(order_id: int, db: Db, _: AdminUser) -> OrderOut:
    return _order_out(db, production.cancel_order(db, order_id))
