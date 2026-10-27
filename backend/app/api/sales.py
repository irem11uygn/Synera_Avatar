"""Satışlar: liste, ayrıntı ve mağaza (web) satışı. Araç satışları telefondan /sync/push ile gelir."""

from datetime import date
from decimal import Decimal

from fastapi import APIRouter
from pydantic import BaseModel, Field
from sqlalchemy import select

from app.api.deps import Db, StoreUser, WebUser
from app.api.fields import UtcDateTime
from app.domain.clock import business_day_bounds_utc
from app.models import Sale
from app.models.enums import BaseUnit, PaymentMethod, SaleChannel
from app.services.lookups import get_or_404
from app.services.sales import SaleView, StoreLineInput, create_store_sale, sale_view

router = APIRouter(prefix="/sales", tags=["satış"])


class SaleLineOut(BaseModel):
    id: int  # iade ve ikinci kademe kaydı bu kimlikle yapılır
    line_no: int
    lot_no: str
    product_name: str
    base_unit: BaseUnit
    qty: Decimal
    unit_price: Decimal
    amount: Decimal
    cost_amount: Decimal


class SaleOut(BaseModel):
    id: int
    sale_no: str
    client_uuid: str
    channel: SaleChannel
    customer_id: int
    customer_name: str
    warehouse_id: int
    seller_name: str
    payment_method: PaymentMethod | None
    device_id: str | None
    sold_at: UtcDateTime
    received_at: UtcDateTime
    recall_violation: bool
    lines: list[SaleLineOut]
    total_amount: Decimal
    total_cost: Decimal


def _sale_out(view: SaleView) -> SaleOut:
    sale = view.sale
    return SaleOut(
        id=sale.id,
        sale_no=sale.sale_no,
        client_uuid=sale.client_uuid,
        channel=sale.channel,
        customer_id=sale.customer_id,
        customer_name=view.customer_name,
        warehouse_id=sale.warehouse_id,
        seller_name=view.seller_name,
        payment_method=sale.payment_method,
        device_id=sale.device_id,
        sold_at=sale.sold_at,
        received_at=sale.received_at,
        recall_violation=sale.recall_violation,
        lines=[SaleLineOut(**vars(line)) for line in view.lines],
        total_amount=view.total_amount,
        total_cost=view.total_cost,
    )


class StoreLineIn(BaseModel):
    lot_no: str = Field(min_length=1, max_length=40)
    qty: Decimal = Field(gt=0, max_digits=12, decimal_places=3)
    unit_price: Decimal | None = Field(
        default=None, ge=0, max_digits=14, decimal_places=4
    )  # boşsa liste fiyatı


class StoreSaleIn(BaseModel):
    customer_id: int
    warehouse_id: int
    payment_method: PaymentMethod
    lines: list[StoreLineIn] = Field(min_length=1, max_length=50)


@router.post("", response_model=SaleOut, status_code=201)
def create(body: StoreSaleIn, db: Db, user: StoreUser) -> SaleOut:
    """Mağaza satışı: ana depodan, anlık. Geri çağrılmış ya da son kullanma tarihi geçmiş parti satılamaz."""
    sale = create_store_sale(
        db,
        user,
        customer_id=body.customer_id,
        warehouse_id=body.warehouse_id,
        payment_method=body.payment_method,
        lines=[StoreLineInput(line.lot_no, line.qty, line.unit_price) for line in body.lines],
    )
    return _sale_out(sale_view(db, sale))


@router.get("", response_model=list[SaleOut])
def list_sales(db: Db, _: WebUser, day: date | None = None) -> list[SaleOut]:
    """Satışlar, yeniden eskiye. `day` verilirse yalnız o iş günü (yerel saat)."""
    query = select(Sale).order_by(Sale.id.desc())
    if day is not None:
        start, end = business_day_bounds_utc(day)
        query = query.where(Sale.sold_at >= start, Sale.sold_at < end)
    return [_sale_out(sale_view(db, s)) for s in db.scalars(query)]


@router.get("/{sale_id}", response_model=SaleOut)
def get_sale(sale_id: int, db: Db, _: WebUser) -> SaleOut:
    return _sale_out(sale_view(db, get_or_404(db, Sale, sale_id, "Satış")))
