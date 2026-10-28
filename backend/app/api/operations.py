"""Günlük işler: ana sayfa özeti, gün sonu ve depo/araç sayımı."""

from datetime import date
from decimal import Decimal

from fastapi import APIRouter
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select

from app.api.deps import CountUser, Db, SellerUser, StoreUser, WebUser
from app.api.fields import UtcDateTime
from app.domain.clock import business_today
from app.models import StockCount, User, Warehouse
from app.models.enums import BaseUnit, PaymentMethod, SaleChannel, Severity
from app.services import alarms, audit
from app.services.charts import charts, fill_rate
from app.services.dashboard import EXPIRY_WARNING_DAYS, dashboard
from app.services.day_end import day_end
from app.services.lookups import get_or_404
from app.services.stock_count import CountLineInput, count_lines, record_count

router = APIRouter(tags=["günlük işler"])


class _FromModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# --- Ana sayfa ---


class ExpiringLotOut(_FromModel):
    lot_no: str
    product_name: str
    base_unit: BaseUnit
    expiry_date: date
    days_left: int
    qty: Decimal
    warehouses: list[str]
    blocked: bool


class LowStockOut(_FromModel):
    product_id: int
    product_code: str
    product_name: str
    base_unit: BaseUnit
    qty: Decimal
    min_stock: Decimal


class OpenRecallOut(_FromModel):
    id: int
    recall_no: str
    lot_no: str
    started_at: UtcDateTime


class DashboardOut(_FromModel):
    today: date
    expiry_warning_days: int
    expiring: list[ExpiringLotOut]
    low_stock: list[LowStockOut]
    open_recalls: list[OpenRecallOut]
    unread_alerts: int
    draft_orders: int
    shipped_orders: int
    draft_cuttings: int
    today_sale_count: int
    today_sales_amount: Decimal
    stock_value: Decimal


@router.get("/dashboard", response_model=DashboardOut)
def get_dashboard(db: Db, user: WebUser) -> DashboardOut:
    """Bugün ilgilenilecek işler: SKT'si yaklaşan/geçen partiler, kritik stok, açık geri çağırmalar."""
    data = dashboard(db, alarms.visible_kinds(user))
    return DashboardOut.model_validate({**vars(data), "expiry_warning_days": EXPIRY_WARNING_DAYS})


class EkpPointOut(_FromModel):
    label: str
    day: date
    actual: Decimal
    forecast: Decimal | None


class SliceOut(_FromModel):
    label: str
    value: Decimal


class PartCostOut(_FromModel):
    label: str
    kg: Decimal
    unit_cost: Decimal


class ShipmentOut(_FromModel):
    customer: str
    qty_by_unit: dict[str, Decimal]
    amount: Decimal


class ChartsOut(_FromModel):
    ekp_history: list[EkpPointOut]
    ekp_synthetic: list[EkpPointOut]
    target_qty: Decimal
    actual_qty: Decimal
    fill_rate_pct: Decimal | None
    target_label: str
    cost_order_no: str | None
    cost_slices: list[SliceOut]
    cost_ekp: Decimal | None
    parts_cutting_no: str | None
    part_costs: list[PartCostOut]
    shipments: list[ShipmentOut]


@router.get("/dashboard/charts", response_model=ChartsOut)
def get_charts(db: Db, _: WebUser) -> ChartsOut:
    """Panel grafikleri: EKP geçmişi ve model tahmini, hedef/gerçekleşen, maliyet dağılımı, sevkiyat."""
    data = charts(db)
    return ChartsOut.model_validate(
        {**vars(data), "fill_rate_pct": fill_rate(data.target_qty, data.actual_qty)}
    )


# --- Gün sonu ---


class DaySaleOut(_FromModel):
    id: int
    sale_no: str
    sold_at: UtcDateTime
    channel: SaleChannel
    customer_name: str
    seller_name: str
    payment_method: PaymentMethod | None
    amount: Decimal
    recall_violation: bool


class DayTotalOut(_FromModel):
    key: str
    sale_count: int
    amount: Decimal


class DayReturnOut(_FromModel):
    return_no: str
    sale_no: str
    customer_name: str
    lot_no: str
    qty: Decimal
    refund_amount: Decimal


class StockLeftOut(_FromModel):
    lot_no: str
    product_name: str
    base_unit: BaseUnit
    expiry_date: date | None
    qty: Decimal


class DayEndOut(_FromModel):
    day: date
    sale_count: int
    sales_amount: Decimal
    cost_amount: Decimal
    refund_amount: Decimal
    net_amount: Decimal
    by_payment: list[DayTotalOut]
    by_seller: list[DayTotalOut]
    sales: list[DaySaleOut]
    returns: list[DayReturnOut]
    stock_left: list[StockLeftOut]


@router.get("/day-end", response_model=DayEndOut)
def get_day_end(
    db: Db,
    _: StoreUser,
    day: date | None = None,
    user_id: int | None = None,
    warehouse_id: int | None = None,
) -> DayEndOut:
    """Günün satışları ve iadeleri; ödeme türüne ve satıcıya göre toplamlar. Gün boşsa bugün."""
    if user_id is not None:
        get_or_404(db, User, user_id, "Kullanıcı")
    if warehouse_id is not None:
        get_or_404(db, Warehouse, warehouse_id, "Depo")
    result = day_end(db, day or business_today(), user_id=user_id, warehouse_id=warehouse_id)
    return DayEndOut.model_validate(result)


@router.get("/sync/day-end", response_model=DayEndOut, tags=["senkronizasyon"])
def my_day_end(db: Db, user: SellerUser, day: date | None = None) -> DayEndOut:
    """Satış elemanının kendi gün sonu: kendi satışları, iadeleri ve aracında kalan mal."""
    result = day_end(db, day or business_today(), user_id=user.id, warehouse_id=user.warehouse_id)
    return DayEndOut.model_validate(result)


# --- Sayım ---


class CountLineIn(BaseModel):
    lot_no: str = Field(min_length=1, max_length=40)
    counted_qty: Decimal = Field(ge=0, max_digits=12, decimal_places=3)


class StockCountIn(BaseModel):
    warehouse_id: int
    note: str | None = Field(default=None, max_length=255)
    lines: list[CountLineIn] = Field(min_length=1, max_length=500)


class CountLineOut(_FromModel):
    lot_no: str
    product_name: str
    base_unit: BaseUnit
    system_qty: Decimal
    counted_qty: Decimal
    difference: Decimal
    shortage_value: Decimal


class StockCountOut(BaseModel):
    id: int
    count_no: str
    warehouse_id: int
    warehouse_code: str
    note: str | None
    counted_by: str
    created_at: UtcDateTime
    lines: list[CountLineOut]
    shortage_value: Decimal  # eksiklerin toplam maliyeti (fire olarak yazıldı)
    surplus_lines: int  # fazla çıkan parti sayısı (araştırılmalı)


def _count_out(db: Db, count: StockCount) -> StockCountOut:
    warehouse = db.get(Warehouse, count.warehouse_id)
    user = db.get(User, count.created_by) if count.created_by is not None else None
    lines = [CountLineOut.model_validate(line) for line in count_lines(db, count)]
    return StockCountOut(
        id=count.id,
        count_no=count.count_no,
        warehouse_id=count.warehouse_id,
        warehouse_code=warehouse.code if warehouse else "",
        note=count.note,
        counted_by=user.full_name if user else "",
        created_at=count.created_at,
        lines=lines,
        shortage_value=sum((line.shortage_value for line in lines), Decimal("0.00")),
        surplus_lines=sum(1 for line in lines if line.difference > 0),
    )


@router.post("/stock-counts", response_model=StockCountOut, status_code=201)
def create_count(body: StockCountIn, db: Db, user: CountUser) -> StockCountOut:
    """Sayılan miktarlar kaydedilir; eksik çıkan mal "Sayım farkı" firesiyle düşülür, fazlası raporlanır.
    Satış elemanı yalnız kendi aracını sayar."""
    count = record_count(
        db,
        user,
        warehouse_id=body.warehouse_id,
        note=body.note,
        lines=[CountLineInput(line.lot_no, line.counted_qty) for line in body.lines],
    )
    out = _count_out(db, count)
    short = [line for line in out.lines if line.difference < 0]
    audit.log(
        db,
        "SAYIM",
        f"Sayım {out.count_no} ({out.warehouse_code}): {len(out.lines)} lot, {len(short)} eksik"
        + (f", eksik değeri {sum((line.shortage_value for line in short), Decimal(0))} €" if short else ""),
        user=user,
        severity=Severity.UYARI if short else Severity.BILGI,
        ref_type="STOCK_COUNT",
        ref_id=count.id,
    )
    alarms.stock_count_difference(
        db,
        user,
        count_id=count.id,
        count_no=out.count_no,
        warehouse_code=out.warehouse_code,
        differences=[
            (
                line.lot_no,
                line.product_name,
                "adet" if line.base_unit == BaseUnit.ADET else "kg",
                line.difference,
            )
            for line in out.lines
            if line.difference != 0
        ],
        shortage_value=sum((line.shortage_value for line in short), Decimal(0)),
    )
    return out


@router.get("/stock-counts", response_model=list[StockCountOut])
def list_counts(db: Db, _: WebUser) -> list[StockCountOut]:
    return [_count_out(db, c) for c in db.scalars(select(StockCount).order_by(StockCount.id.desc()))]


@router.get("/stock-counts/{count_id}", response_model=StockCountOut)
def get_count(count_id: int, db: Db, _: WebUser) -> StockCountOut:
    return _count_out(db, get_or_404(db, StockCount, count_id, "Sayım"))
