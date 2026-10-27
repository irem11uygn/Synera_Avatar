"""Stok firesi/imhası ve hatalı hareketin ters kaydı (FR-303, NFR-002)."""

from decimal import Decimal

from fastapi import APIRouter
from pydantic import BaseModel, Field
from sqlalchemy import select

from app.api.deps import Db, StockUser, WebUser
from app.api.fields import UtcDateTime
from app.models import Adjustment, Lot, Warehouse
from app.models.enums import MovementType
from app.services.adjustments import create_adjustment, reverse
from app.services.lookups import lot_by_no

router = APIRouter(tags=["transfer"])


class AdjustmentIn(BaseModel):
    lot_no: str
    warehouse_id: int
    qty: Decimal = Field(gt=0, max_digits=12, decimal_places=3)
    reason: str = Field(min_length=1, max_length=255)


class AdjustmentOut(BaseModel):
    id: int
    adj_no: str
    lot_no: str
    warehouse_code: str
    qty: Decimal
    reason: str
    created_at: UtcDateTime


class ReverseIn(BaseModel):
    reason: str = Field(min_length=1, max_length=255)


class ReversalOut(BaseModel):
    id: int
    reversal_of_id: int
    type: MovementType
    lot_no: str
    warehouse_code: str
    qty: Decimal
    value: Decimal


def _adjustment_rows(db: Db, *conditions: object) -> list[AdjustmentOut]:
    rows = db.execute(
        select(Adjustment, Lot.lot_no, Warehouse.code)
        .join(Lot, Lot.id == Adjustment.lot_id)
        .join(Warehouse, Warehouse.id == Adjustment.warehouse_id)
        .where(*conditions)
        .order_by(Adjustment.id.desc())
    ).all()
    return [
        AdjustmentOut(
            id=a.id,
            adj_no=a.adj_no,
            lot_no=lot_no,
            warehouse_code=code,
            qty=a.qty,
            reason=a.reason,
            created_at=a.created_at,
        )
        for a, lot_no, code in rows
    ]


@router.post("/adjustments", response_model=AdjustmentOut, status_code=201)
def create(body: AdjustmentIn, db: Db, user: StockUser) -> AdjustmentOut:
    record = create_adjustment(
        db,
        lot_id=lot_by_no(db, body.lot_no.strip()).id,
        warehouse_id=body.warehouse_id,
        qty=body.qty,
        reason=body.reason,
        user_id=user.id,
    )
    return _adjustment_rows(db, Adjustment.id == record.id)[0]


@router.get("/adjustments", response_model=list[AdjustmentOut])
def list_adjustments(db: Db, _: WebUser) -> list[AdjustmentOut]:
    return _adjustment_rows(db)


@router.post("/movements/{movement_id}/reverse", response_model=list[ReversalOut], status_code=201)
def reverse_one(movement_id: int, body: ReverseIn, db: Db, user: StockUser) -> list[ReversalOut]:
    """Hareketi silmeden düzeltir: aslının tam tersi yeni hareket(ler) yazılır (gerekçe zorunlu)."""
    reversals = reverse(db, movement_id, body.reason, user.id)
    lot_ids = [m.lot_id for m in reversals]
    names = {lot_id: no for lot_id, no in db.execute(select(Lot.id, Lot.lot_no).where(Lot.id.in_(lot_ids)))}
    codes = {wid: code for wid, code in db.execute(select(Warehouse.id, Warehouse.code))}
    return [
        ReversalOut(
            id=m.id,
            reversal_of_id=m.reversal_of_id or 0,
            type=m.type,
            lot_no=names[m.lot_id],
            warehouse_code=codes[m.warehouse_id],
            qty=m.qty,
            value=m.value,
        )
        for m in reversals
    ]
