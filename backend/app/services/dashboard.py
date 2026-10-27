"""Ana sayfa özeti: bugün ilgilenilmesi gereken işler (SKT, kritik stok, geri çağırma, bekleyen belgeler).

Son kullanma ve kritik stok, işletmenin elindeki mala bakar: ana depo ve satış araçları. Fasoncunun
deposundaki mal (hammadde) üretimde tüketileceği için kritik stok hesabına girmez.
"""

from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from decimal import Decimal

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.domain.clock import business_day_bounds_utc, business_today
from app.models import (
    Alert,
    Cutting,
    Lot,
    Product,
    ProductionOrder,
    Recall,
    Sale,
    SaleLine,
    StockBalance,
    Warehouse,
)
from app.models.enums import BaseUnit, CuttingStatus, LotStatus, ProductionStatus, RecallStatus, WarehouseKind

EXPIRY_WARNING_DAYS = 3
OWN_STOCK = (WarehouseKind.ANA, WarehouseKind.ARAC)


@dataclass(frozen=True)
class ExpiringLot:
    lot_no: str
    product_name: str
    base_unit: BaseUnit
    expiry_date: date
    days_left: int  # eksi: süresi geçmiş
    qty: Decimal
    warehouses: list[str]
    blocked: bool


@dataclass(frozen=True)
class LowStock:
    product_id: int
    product_code: str
    product_name: str
    base_unit: BaseUnit
    qty: Decimal
    min_stock: Decimal


@dataclass(frozen=True)
class OpenRecall:
    id: int
    recall_no: str
    lot_no: str
    started_at: datetime


@dataclass(frozen=True)
class Dashboard:
    today: date
    expiring: list[ExpiringLot]  # süresi geçmiş + EXPIRY_WARNING_DAYS içinde dolacak, stokta olanlar
    low_stock: list[LowStock]
    open_recalls: list[OpenRecall]
    unread_alerts: int
    draft_orders: int
    shipped_orders: int  # fasoncuya gönderilmiş, teslim alınmayı bekleyen
    draft_cuttings: int
    today_sale_count: int
    today_sales_amount: Decimal
    stock_value: Decimal


def dashboard(session: Session) -> Dashboard:
    today = business_today()
    start, end = business_day_bounds_utc(today)
    order_counts = dict(
        session.execute(select(ProductionOrder.status, func.count()).group_by(ProductionOrder.status)).all()
    )
    today_sales = session.execute(
        select(func.count(func.distinct(Sale.id)), func.coalesce(func.sum(SaleLine.amount), 0))
        .select_from(Sale)
        .join(SaleLine, SaleLine.sale_id == Sale.id)
        .where(Sale.sold_at >= start, Sale.sold_at < end)
    ).one()
    return Dashboard(
        today=today,
        expiring=_expiring(session, today),
        low_stock=_low_stock(session, today),
        open_recalls=[
            OpenRecall(id=recall.id, recall_no=recall.recall_no, lot_no=lot_no, started_at=recall.started_at)
            for recall, lot_no in session.execute(
                select(Recall, Lot.lot_no)
                .join(Lot, Lot.id == Recall.source_lot_id)
                .where(Recall.status == RecallStatus.ACIK)
                .order_by(Recall.id)
            )
        ],
        unread_alerts=session.scalar(
            select(func.count()).select_from(Alert).where(Alert.acknowledged_at.is_(None))
        )
        or 0,
        draft_orders=order_counts.get(ProductionStatus.TASLAK, 0),
        shipped_orders=order_counts.get(ProductionStatus.SEVK_EDILDI, 0),
        draft_cuttings=session.scalar(
            select(func.count()).select_from(Cutting).where(Cutting.status == CuttingStatus.TASLAK)
        )
        or 0,
        today_sale_count=today_sales[0],
        today_sales_amount=Decimal(today_sales[1]).quantize(Decimal("0.01")),
        stock_value=Decimal(
            session.scalar(
                select(func.coalesce(func.sum(Lot.remaining_value), 0)).where(Lot.remaining_qty > 0)
            )
            or 0
        ).quantize(Decimal("0.01")),
    )


def _expiring(session: Session, today: date) -> list[ExpiringLot]:
    limit = today + timedelta(days=EXPIRY_WARNING_DAYS)
    rows = session.execute(
        select(Lot, Product.name, Product.base_unit, Warehouse.code, StockBalance.qty)
        .join(StockBalance, StockBalance.lot_id == Lot.id)
        .join(Warehouse, Warehouse.id == StockBalance.warehouse_id)
        .join(Product, Product.id == Lot.product_id)
        .where(
            StockBalance.qty > 0,
            Warehouse.kind.in_(OWN_STOCK),
            Lot.expiry_date.is_not(None),
            Lot.expiry_date <= limit,
        )
        .order_by(Lot.expiry_date, Lot.lot_no, Warehouse.code)
    ).all()
    lots: dict[int, tuple[Lot, str, BaseUnit]] = {}
    codes: dict[int, list[str]] = defaultdict(list)
    qtys: dict[int, Decimal] = defaultdict(Decimal)
    for lot, name, unit, code, qty in rows:
        lots[lot.id] = (lot, name, unit)
        codes[lot.id].append(code)
        qtys[lot.id] += qty
    return [
        ExpiringLot(
            lot_no=lot.lot_no,
            product_name=name,
            base_unit=unit,
            expiry_date=lot.expiry_date,
            days_left=(lot.expiry_date - today).days,
            qty=qtys[lot_id],
            warehouses=codes[lot_id],
            blocked=lot.status == LotStatus.BLOKE,
        )
        for lot_id, (lot, name, unit) in lots.items()
        if lot.expiry_date is not None
    ]


def _low_stock(session: Session, today: date) -> list[LowStock]:
    """Satılabilir stok: aktif ve süresi geçmemiş partiler."""
    products = session.scalars(
        select(Product).where(Product.min_stock.is_not(None), Product.active.is_(True)).order_by(Product.code)
    ).all()
    if not products:
        return []
    totals: dict[int, Decimal] = defaultdict(Decimal)
    for product_id, qty in session.execute(
        select(Lot.product_id, func.sum(StockBalance.qty))
        .join(StockBalance, StockBalance.lot_id == Lot.id)
        .join(Warehouse, Warehouse.id == StockBalance.warehouse_id)
        .where(
            Warehouse.kind.in_(OWN_STOCK),
            Lot.status == LotStatus.AKTIF,
            or_(Lot.expiry_date.is_(None), Lot.expiry_date >= today),
            Lot.product_id.in_([p.id for p in products]),
        )
        .group_by(Lot.product_id)
    ):
        totals[product_id] = Decimal(qty)
    return [
        LowStock(
            product_id=p.id,
            product_code=p.code,
            product_name=p.name,
            base_unit=p.base_unit,
            qty=totals[p.id],
            min_stock=p.min_stock,
        )
        for p in products
        if p.min_stock is not None and totals[p.id] < p.min_stock
    ]
