"""Yeniden işleme (FR-303): işletme içinde lotlardan yeni lot (ör. iadenin yeniden paketlenmesi)."""

from datetime import date
from decimal import Decimal

from fastapi import APIRouter
from pydantic import BaseModel, Field
from sqlalchemy import select

from app.api.deps import Db, ProductionUser, WebUser
from app.api.fields import UtcDateTime
from app.models import Lot, Product, ProductionInput, ProductionOrder, StockMovement
from app.models.enums import BaseUnit, DocType, MovementType, ProductionKind
from app.services.lookups import lot_by_no
from app.services.reprocessing import ReprocessInput, reprocess

router = APIRouter(prefix="/reprocessing", tags=["yeniden işleme"])


class ReprocessInputIn(BaseModel):
    lot_no: str
    qty: Decimal = Field(gt=0, max_digits=12, decimal_places=3)


class ReprocessIn(BaseModel):
    inputs: list[ReprocessInputIn] = Field(min_length=1)
    output_product_id: int
    output_qty: Decimal = Field(gt=0, max_digits=12, decimal_places=3)
    extra_cost: Decimal = Field(default=Decimal("0.00"), ge=0, max_digits=14, decimal_places=2)
    note: str | None = Field(default=None, max_length=500)
    output_lot_no: str | None = Field(default=None, max_length=40)
    warehouse_id: int | None = None


class ReprocessInputOut(BaseModel):
    lot_no: str
    product_name: str
    base_unit: BaseUnit
    qty: Decimal
    value: Decimal


class ReprocessOut(BaseModel):
    id: int
    order_no: str
    completed_at: UtcDateTime | None
    output_lot_no: str | None
    output_product_name: str
    base_unit: BaseUnit
    output_qty: Decimal
    inputs: list[ReprocessInputOut]
    consumed_value: Decimal
    extra_cost: Decimal
    total_value: Decimal
    unit_cost: Decimal | None
    expiry_date: date | None
    note: str | None


def _out(db: Db, order: ProductionOrder) -> ReprocessOut:
    product = db.get(Product, order.output_product_id)
    lot = db.get(Lot, order.output_lot_id) if order.output_lot_id else None
    assert product is not None
    values = {
        lot_id: -value
        for lot_id, value in db.execute(
            select(StockMovement.lot_id, StockMovement.value).where(
                StockMovement.doc_type == DocType.URETIM,
                StockMovement.doc_id == order.id,
                StockMovement.type == MovementType.URETIM_TUKETIM,
            )
        )
    }
    rows = db.execute(
        select(ProductionInput, Lot.lot_no, Product.name, Product.base_unit)
        .join(Lot, Lot.id == ProductionInput.lot_id)
        .join(Product, Product.id == Lot.product_id)
        .where(ProductionInput.order_id == order.id)
        .order_by(ProductionInput.id)
    ).all()
    inputs = [
        ReprocessInputOut(
            lot_no=lot_no,
            product_name=name,
            base_unit=unit,
            qty=row.consumed_qty,
            value=values.get(row.lot_id, 0),
        )
        for row, lot_no, name, unit in rows
    ]
    consumed = sum((i.value for i in inputs), Decimal("0.00"))
    extra = order.service_amount or Decimal("0.00")
    return ReprocessOut(
        id=order.id,
        order_no=order.order_no,
        completed_at=order.completed_at,
        output_lot_no=lot.lot_no if lot else None,
        output_product_name=product.name,
        base_unit=product.base_unit,
        output_qty=order.received_qty or order.planned_qty,
        inputs=inputs,
        consumed_value=consumed,
        extra_cost=extra,
        total_value=lot.initial_value if lot else consumed + extra,
        unit_cost=lot.unit_cost if lot else None,
        expiry_date=lot.expiry_date if lot else None,
        note=order.service_note,
    )


@router.post("", response_model=ReprocessOut, status_code=201)
def create(body: ReprocessIn, db: Db, user: ProductionUser) -> ReprocessOut:
    order = reprocess(
        db,
        inputs=[ReprocessInput(lot_by_no(db, i.lot_no.strip()).id, i.qty) for i in body.inputs],
        output_product_id=body.output_product_id,
        output_qty=body.output_qty,
        extra_cost=body.extra_cost,
        note=body.note,
        output_lot_no=(body.output_lot_no or "").strip() or None,
        warehouse_id=body.warehouse_id,
        user_id=user.id,
    )
    return _out(db, order)


@router.get("", response_model=list[ReprocessOut])
def list_reprocessing(db: Db, _: WebUser) -> list[ReprocessOut]:
    orders = db.scalars(
        select(ProductionOrder)
        .where(ProductionOrder.kind == ProductionKind.YENIDEN_ISLEME)
        .order_by(ProductionOrder.id.desc())
    )
    return [_out(db, order) for order in orders]
