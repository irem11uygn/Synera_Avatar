"""Stok: ürün / lot / depo kırılımında bakiyeler (FR-104). Bakiyeler defterden türetilen özettir."""

from datetime import date
from decimal import Decimal

from fastapi import APIRouter
from pydantic import BaseModel
from sqlalchemy import select

from app.api.deps import AdminUser, Db
from app.models import Lot, Product, StockBalance, Warehouse
from app.models.enums import BaseUnit, LotStatus

router = APIRouter(prefix="/stock", tags=["stok"])


class StockRowOut(BaseModel):
    lot_no: str
    lot_status: LotStatus
    expiry_date: date | None
    unit_cost: Decimal
    product_id: int
    product_code: str
    product_name: str
    base_unit: BaseUnit
    warehouse_id: int
    warehouse_code: str
    warehouse_name: str
    qty: Decimal


@router.get("", response_model=list[StockRowOut])
def list_stock(
    db: Db, _: AdminUser, warehouse_id: int | None = None, product_id: int | None = None
) -> list[StockRowOut]:
    query = (
        select(StockBalance.qty, Lot, Product, Warehouse)
        .join(Lot, Lot.id == StockBalance.lot_id)
        .join(Product, Product.id == Lot.product_id)
        .join(Warehouse, Warehouse.id == StockBalance.warehouse_id)
        .where(StockBalance.qty != 0)
        .order_by(Warehouse.id, Product.code, Lot.expiry_date, Lot.lot_no)
    )
    if warehouse_id is not None:
        query = query.where(StockBalance.warehouse_id == warehouse_id)
    if product_id is not None:
        query = query.where(Lot.product_id == product_id)
    return [
        StockRowOut(
            lot_no=lot.lot_no,
            lot_status=lot.status,
            expiry_date=lot.expiry_date,
            unit_cost=lot.unit_cost,
            product_id=product.id,
            product_code=product.code,
            product_name=product.name,
            base_unit=product.base_unit,
            warehouse_id=warehouse.id,
            warehouse_code=warehouse.code,
            warehouse_name=warehouse.name,
            qty=qty,
        )
        for qty, lot, product, warehouse in db.execute(query)
    ]
