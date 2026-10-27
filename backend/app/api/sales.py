"""Satışlar — yönetici görünümü (api.md §2 Satış). Android satışları /sync/push ile gelir."""

from decimal import Decimal

from fastapi import APIRouter
from pydantic import BaseModel
from sqlalchemy import select

from app.api.deps import AdminUser, Db
from app.api.fields import UtcDateTime
from app.models import Sale
from app.models.enums import BaseUnit, SaleChannel
from app.services.lookups import get_or_404
from app.services.sales import SaleView, sale_view

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
        device_id=sale.device_id,
        sold_at=sale.sold_at,
        received_at=sale.received_at,
        recall_violation=sale.recall_violation,
        lines=[SaleLineOut(**vars(line)) for line in view.lines],
        total_amount=view.total_amount,
        total_cost=view.total_cost,
    )


@router.get("", response_model=list[SaleOut])
def list_sales(db: Db, _: AdminUser) -> list[SaleOut]:
    return [_sale_out(sale_view(db, s)) for s in db.scalars(select(Sale).order_by(Sale.id.desc()))]


@router.get("/{sale_id}", response_model=SaleOut)
def get_sale(sale_id: int, db: Db, _: AdminUser) -> SaleOut:
    return _sale_out(sale_view(db, get_or_404(db, Sale, sale_id, "Satış")))
