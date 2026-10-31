"""Lotlar, depo bakiyeleri, hareket geçmişi (FR-104, FR-112) ve kalite blokesi (karantina)."""

from datetime import date
from decimal import Decimal
from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel, Field
from sqlalchemy import select

from app.api.deps import Db, QualityUser, WebUser
from app.api.fields import UtcDateTime
from app.models import Lot, LotLink, Partner, Product, StockBalance, StockMovement, User, Warehouse
from app.models.enums import BaseUnit, DocType, LinkProcess, LotOrigin, LotStatus, MovementType, Severity
from app.services import audit
from app.services.lookups import document_numbers, lot_by_no
from app.services.quality import holds_of, open_recalls_of, place_hold, release_hold

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


class HoldOut(BaseModel):
    id: int
    reason: str
    placed_by_name: str | None
    placed_at: UtcDateTime
    released_by_name: str | None
    released_at: UtcDateTime | None
    release_note: str | None


class LotDetailOut(LotOut):
    balances: list[BalanceOut]
    parents: list[LinkOut]
    children: list[LinkOut]
    holds: list[HoldOut]  # kalite blokeleri, yeniden eskiye; açık olanın released_at'i boş
    open_recalls: list[str]  # lotu kapalı tutan açık geri çağırmalar


class HoldIn(BaseModel):
    reason: str = Field(min_length=1, max_length=500)


class ReleaseIn(BaseModel):
    note: str | None = Field(default=None, max_length=500)


class MovementOut(BaseModel):
    id: int
    posted_at: UtcDateTime
    type: MovementType
    warehouse_code: str
    qty: Decimal
    value: Decimal
    doc_type: DocType
    doc_id: int
    doc_no: str | None
    user_name: str | None  # örnek kayıtlarda boş
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
    _: WebUser,
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
def get_lot(lot_no: str, db: Db, _: WebUser) -> dict:
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

    def name(user_id: int | None) -> str | None:
        user = db.get(User, user_id) if user_id else None
        return user.full_name if user else None

    return {
        **_lot_out(db, lot),
        "balances": [BalanceOut(warehouse_code=b[0], warehouse_name=b[1], qty=b[2]) for b in balances],
        "parents": links(LotLink.child_lot_id, LotLink.parent_lot_id),
        "children": links(LotLink.parent_lot_id, LotLink.child_lot_id),
        "holds": [
            HoldOut(
                id=h.id,
                reason=h.reason,
                placed_by_name=name(h.placed_by),
                placed_at=h.placed_at,
                released_by_name=name(h.released_by),
                released_at=h.released_at,
                release_note=h.release_note,
            )
            for h in holds_of(db, lot.id)
        ],
        "open_recalls": open_recalls_of(db, lot.id),
    }


@router.post("/{lot_no}/hold", response_model=LotDetailOut)
def hold_lot(lot_no: str, body: HoldIn, db: Db, user: QualityUser) -> dict:
    """Kalite blokesi: lot soruşturma bitene kadar satışa ve kullanıma kapanır (türevlerine dokunmaz)."""
    hold = place_hold(db, lot_no=lot_no, reason=body.reason, user=user)
    lot = lot_by_no(db, lot_no)
    audit.log(
        db,
        "KALITE_BLOKESI",
        f"{lot.lot_no} kalite blokesine alındı: {hold.reason}",
        user=user,
        severity=Severity.UYARI,
        ref_type="LOT",
        ref_id=lot.id,
    )
    return get_lot(lot_no, db, user)


@router.post("/{lot_no}/release", response_model=LotDetailOut)
def release_lot(lot_no: str, body: ReleaseIn, db: Db, user: QualityUser) -> dict:
    """Kalite blokesini kaldırır; lot açık bir geri çağırmada değilse yeniden satışa açılır."""
    hold, recalls = release_hold(db, lot_no=lot_no, note=body.note, user=user)
    lot = lot_by_no(db, lot_no)
    state = f"hâlâ geri çağırmada ({', '.join(recalls)}), satışa kapalı" if recalls else "yeniden satışa açık"
    audit.log(
        db,
        "KALITE_BLOKESI_KALDIRILDI",
        f"{lot.lot_no} kalite blokesi kaldırıldı; {state}"
        + (f" — {hold.release_note}" if hold.release_note else ""),
        user=user,
        ref_type="LOT",
        ref_id=lot.id,
    )
    return get_lot(lot_no, db, user)


@router.get("/{lot_no}/movements", response_model=list[MovementOut])
def lot_movements(lot_no: str, db: Db, _: WebUser) -> list[MovementOut]:
    lot = lot_by_no(db, lot_no)
    rows = db.execute(
        select(StockMovement, Warehouse.code, User.full_name)
        .join(Warehouse, Warehouse.id == StockMovement.warehouse_id)
        .outerjoin(User, User.id == StockMovement.user_id)
        .where(StockMovement.lot_id == lot.id)
        .order_by(StockMovement.id)
    ).all()
    numbers = document_numbers(db, ((m.doc_type, m.doc_id) for m, _, _ in rows))
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
            doc_no=numbers.get((m.doc_type, m.doc_id)),
            user_name=user_name,
            note=m.note,
            reversal_of_id=m.reversal_of_id,
        )
        for m, code, user_name in rows
    ]
