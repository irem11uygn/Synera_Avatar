"""Depolar arası transfer (FR-303), ör. araç deposuna yükleme."""

from datetime import datetime
from decimal import Decimal

from fastapi import APIRouter
from pydantic import BaseModel, Field
from sqlalchemy import select

from app.api.deps import AdminUser, Db
from app.models import Lot, Transfer, TransferLine, Warehouse
from app.models.enums import TransferReason
from app.services.lookups import lot_by_no
from app.services.transfers import TransferLineInput, create_transfer

router = APIRouter(prefix="/transfers", tags=["transfer"])


class TransferLineIn(BaseModel):
    lot_no: str
    qty: Decimal = Field(gt=0, max_digits=12, decimal_places=3)


class TransferIn(BaseModel):
    from_warehouse_id: int
    to_warehouse_id: int
    reason: TransferReason = TransferReason.ARAC_YUKLEME
    lines: list[TransferLineIn] = Field(min_length=1)


class TransferLineOut(BaseModel):
    lot_no: str
    qty: Decimal


class TransferOut(BaseModel):
    id: int
    transfer_no: str
    from_warehouse_code: str
    to_warehouse_code: str
    reason: TransferReason
    production_order_id: int | None
    transferred_at: datetime
    lines: list[TransferLineOut]


def _transfer_out(db: Db, transfer: Transfer) -> TransferOut:
    codes = dict(db.execute(select(Warehouse.id, Warehouse.code)).all())
    lines = db.execute(
        select(Lot.lot_no, TransferLine.qty)
        .join(TransferLine, TransferLine.lot_id == Lot.id)
        .where(TransferLine.transfer_id == transfer.id)
        .order_by(TransferLine.id)
    ).all()
    return TransferOut(
        id=transfer.id,
        transfer_no=transfer.transfer_no,
        from_warehouse_code=codes[transfer.from_warehouse_id],
        to_warehouse_code=codes[transfer.to_warehouse_id],
        reason=transfer.reason,
        production_order_id=transfer.production_order_id,
        transferred_at=transfer.transferred_at,
        lines=[TransferLineOut(lot_no=lot_no, qty=qty) for lot_no, qty in lines],
    )


@router.post("", response_model=TransferOut, status_code=201)
def create(body: TransferIn, db: Db, user: AdminUser) -> TransferOut:
    transfer = create_transfer(
        db,
        from_warehouse_id=body.from_warehouse_id,
        to_warehouse_id=body.to_warehouse_id,
        lines=[TransferLineInput(lot_by_no(db, line.lot_no).id, line.qty) for line in body.lines],
        reason=body.reason,
        user_id=user.id,
    )
    return _transfer_out(db, transfer)


@router.get("", response_model=list[TransferOut])
def list_transfers(db: Db, _: AdminUser) -> list[TransferOut]:
    return [_transfer_out(db, t) for t in db.scalars(select(Transfer).order_by(Transfer.id.desc()))]
