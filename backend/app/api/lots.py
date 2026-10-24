"""Lotlar, depo bakiyeleri ve hareket geçmişi (FR-104, FR-112)."""

from datetime import date, datetime
from decimal import Decimal
from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel
from sqlalchemy import select

from app.api.deps import AdminUser, Db
from app.models import Lot, LotLink, Partner, Product, StockBalance, StockMovement, Warehouse
from app.models.enums import BaseUnit, DocType, LinkProcess, LotOrigin, LotStatus, MovementType
from app.services.lookups import lot_by_no

router = APIRouter(prefix="/lots", tags=["lotlar"])


class LotOut(BaseModel):
    id: int
    lot_no: str
    product_code: str
    product_name: str
    base_unit: BaseUnit
    origin: LotOrigin
    supplier_name: str | None
    status: LotStatus
    initial_qty: Decimal
    initial_value: Decimal
    remaining_qty: Decimal
    remaining_value: Decimal
    unit_cost: Decimal
    produced_at: date | None
    expiry_date: date | None


class BalanceOut(BaseModel):
    warehouse_code: str
    warehouse_name: str
    qty: Decimal


class LinkOut(BaseModel):
    lot_no: str
    qty: Decimal
    process: LinkProcess
    process_id: int


class LotDetailOut(LotOut):
    balances: list[BalanceOut]
    parents: list[LinkOut]
    children: list[LinkOut]


class MovementOut(BaseModel):
    id: int
    posted_at: datetime
    type: MovementType
    warehouse_code: str
    qty: Decimal
    value: Decimal
    doc_type: DocType
    doc_id: int
    note: str | None
    reversal_of_id: int | None


def _lot_out(db: Db, lot: Lot) -> dict:
    product = db.get(Product, lot.product_id)
    supplier = db.get(Partner, lot.supplier_id) if lot.supplier_id else None
    assert product is not None
    return {
        "id": lot.id,
        "lot_no": lot.lot_no,
        "product_code": product.code,
        "product_name": product.name,
        "base_unit": product.base_unit,
        "origin": lot.origin,
        "supplier_name": supplier.name if supplier else None,
        "status": lot.status,
        "initial_qty": lot.initial_qty,
        "initial_value": lot.initial_value,
        "remaining_qty": lot.remaining_qty,
        "remaining_value": lot.remaining_value,
        "unit_cost": lot.unit_cost,
        "produced_at": lot.produced_at,
        "expiry_date": lot.expiry_date,
    }


@router.get("", response_model=list[LotOut])
def list_lots(
    db: Db,
    _: AdminUser,
    product_id: int | None = None,
    status: LotStatus | None = None,
    warehouse_id: int | None = None,
    q: str | None = None,
) -> list[dict]:
    query = select(Lot).order_by(Lot.id.desc())
    if product_id is not None:
        query = query.where(Lot.product_id == product_id)
    if status is not None:
        query = query.where(Lot.status == status)
    if q:
        query = query.where(Lot.lot_no.contains(q))
    if warehouse_id is not None:
        query = query.join(StockBalance, StockBalance.lot_id == Lot.id).where(
            StockBalance.warehouse_id == warehouse_id, StockBalance.qty > 0
        )
    return [_lot_out(db, lot) for lot in db.scalars(query)]


@router.get("/{lot_no}", response_model=LotDetailOut)
def get_lot(lot_no: str, db: Db, _: AdminUser) -> dict:
    lot = lot_by_no(db, lot_no)
    balances = db.execute(
        select(Warehouse.code, Warehouse.name, StockBalance.qty)
        .join(StockBalance, StockBalance.warehouse_id == Warehouse.id)
        .where(StockBalance.lot_id == lot.id, StockBalance.qty != 0)
        .order_by(Warehouse.id)
    ).all()

    def links(own: Any, other: Any) -> list[LinkOut]:
        """own: bu lotun bağlantıdaki sütunu; other: karşı lotun sütunu."""
        rows = db.execute(
            select(Lot.lot_no, LotLink.qty, LotLink.process, LotLink.process_id)
            .join(LotLink, other == Lot.id)
            .where(own == lot.id)
            .order_by(LotLink.id)
        ).all()
        return [LinkOut(lot_no=r[0], qty=r[1], process=r[2], process_id=r[3]) for r in rows]

    return {
        **_lot_out(db, lot),
        "balances": [BalanceOut(warehouse_code=b[0], warehouse_name=b[1], qty=b[2]) for b in balances],
        "parents": links(LotLink.child_lot_id, LotLink.parent_lot_id),
        "children": links(LotLink.parent_lot_id, LotLink.child_lot_id),
    }


@router.get("/{lot_no}/movements", response_model=list[MovementOut])
def lot_movements(lot_no: str, db: Db, _: AdminUser) -> list[MovementOut]:
    lot = lot_by_no(db, lot_no)
    rows = db.execute(
        select(StockMovement, Warehouse.code)
        .join(Warehouse, Warehouse.id == StockMovement.warehouse_id)
        .where(StockMovement.lot_id == lot.id)
        .order_by(StockMovement.id)
    ).all()
    return [
        MovementOut(
            id=m.id,
            posted_at=m.posted_at,
            type=m.type,
            warehouse_code=code,
            qty=m.qty,
            value=m.value,
            doc_type=m.doc_type,
            doc_id=m.doc_id,
            note=m.note,
            reversal_of_id=m.reversal_of_id,
        )
        for m, code in rows
    ]
