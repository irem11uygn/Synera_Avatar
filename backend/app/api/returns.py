"""Müşteri iadesi ve ikinci kademe dağıtım (FR-303, FR-308)."""

from datetime import date
from decimal import Decimal

from fastapi import APIRouter
from pydantic import BaseModel, Field
from sqlalchemy import select

from app.api.deps import AdminUser, Db
from app.api.fields import UtcDateTime
from app.models import CustomerReturn, Lot, OnwardDelivery, Partner, Sale, SaleLine, Warehouse
from app.services.lookups import get_or_404
from app.services.returns import add_onward_delivery, create_return

router = APIRouter(tags=["satış"])


class ReturnIn(BaseModel):
    sale_line_id: int
    qty: Decimal = Field(gt=0, max_digits=12, decimal_places=3)
    warehouse_id: int | None = None  # boşsa ana depo
    reason: str | None = Field(default=None, max_length=255)


class ReturnOut(BaseModel):
    id: int
    return_no: str
    sale_no: str
    customer_name: str
    lot_no: str
    qty: Decimal
    warehouse_code: str
    reason: str | None
    created_at: UtcDateTime


class OnwardIn(BaseModel):
    recipient_partner_id: int
    qty: Decimal = Field(gt=0, max_digits=12, decimal_places=3)
    delivered_at: date | None = None
    source_note: str | None = Field(default=None, max_length=255)


class OnwardOut(BaseModel):
    id: int
    sale_line_id: int
    recipient_partner_id: int
    recipient_name: str
    qty: Decimal
    delivered_at: date | None
    source_note: str | None


def _return_rows(db: Db, *conditions: object) -> list[ReturnOut]:
    rows = db.execute(
        select(CustomerReturn, Sale.sale_no, Partner.name, Lot.lot_no, Warehouse.code)
        .join(SaleLine, SaleLine.id == CustomerReturn.sale_line_id)
        .join(Sale, Sale.id == SaleLine.sale_id)
        .join(Partner, Partner.id == Sale.customer_id)
        .join(Lot, Lot.id == SaleLine.lot_id)
        .join(Warehouse, Warehouse.id == CustomerReturn.warehouse_id)
        .where(*conditions)
        .order_by(CustomerReturn.id.desc())
    ).all()
    return [
        ReturnOut(
            id=r.id,
            return_no=r.return_no,
            sale_no=sale_no,
            customer_name=customer,
            lot_no=lot_no,
            qty=r.qty,
            warehouse_code=code,
            reason=r.reason,
            created_at=r.created_at,
        )
        for r, sale_no, customer, lot_no, code in rows
    ]


@router.post("/returns", response_model=ReturnOut, status_code=201)
def create(body: ReturnIn, db: Db, user: AdminUser) -> ReturnOut:
    """Satılan lot aynı lot numarasıyla depoya geri girer; bloke lota da iade alınır (geri toplama)."""
    record = create_return(
        db,
        sale_line_id=body.sale_line_id,
        qty=body.qty,
        warehouse_id=body.warehouse_id,
        reason=body.reason,
        user_id=user.id,
    )
    return _return_rows(db, CustomerReturn.id == record.id)[0]


@router.get("/returns", response_model=list[ReturnOut])
def list_returns(db: Db, _: AdminUser) -> list[ReturnOut]:
    return _return_rows(db)


def _onward_out(db: Db, delivery: OnwardDelivery) -> OnwardOut:
    partner = db.get(Partner, delivery.recipient_partner_id)
    return OnwardOut(
        id=delivery.id,
        sale_line_id=delivery.sale_line_id,
        recipient_partner_id=delivery.recipient_partner_id,
        recipient_name=partner.name if partner else "",
        qty=delivery.qty,
        delivered_at=delivery.delivered_at,
        source_note=delivery.source_note,
    )


@router.get("/sale-lines/{sale_line_id}/onward-deliveries", response_model=list[OnwardOut])
def list_onward(sale_line_id: int, db: Db, _: AdminUser) -> list[OnwardOut]:
    get_or_404(db, SaleLine, sale_line_id, "Satış satırı")
    deliveries = db.scalars(
        select(OnwardDelivery).where(OnwardDelivery.sale_line_id == sale_line_id).order_by(OnwardDelivery.id)
    )
    return [_onward_out(db, d) for d in deliveries]


@router.post("/sale-lines/{sale_line_id}/onward-deliveries", response_model=OnwardOut, status_code=201)
def create_onward(sale_line_id: int, body: OnwardIn, db: Db, user: AdminUser) -> OnwardOut:
    """Müşterinin bildirdiği ikinci kademe teslimat; izleme listesinde "kesin" olarak görünür."""
    delivery = add_onward_delivery(
        db,
        sale_line_id=sale_line_id,
        recipient_partner_id=body.recipient_partner_id,
        qty=body.qty,
        delivered_at=body.delivered_at,
        source_note=body.source_note,
        user_id=user.id,
    )
    return _onward_out(db, delivery)
