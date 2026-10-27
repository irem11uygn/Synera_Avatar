"""Gün sonu: bir iş günündeki satışlar, ödeme türüne ve satıcıya göre toplamlar, iadeler.

Gün, işletmenin yerel saatine göredir (BUSINESS_UTC_OFFSET_HOURS); satış zamanı satışın yapıldığı an
(çevrimdışı satış sonradan gelse de kendi gününe yazılır). İade tutarı, iade edilen miktarın satıştaki
birim fiyatıyla değeridir — müşteriye geri ödenecek ya da alacaktan düşülecek tutar.
"""

from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.clock import business_day_bounds_utc
from app.domain.money import round_money
from app.models import (
    CustomerReturn,
    Lot,
    Partner,
    Product,
    Sale,
    SaleLine,
    StockBalance,
    StockMovement,
    User,
)
from app.models.enums import BaseUnit, PaymentMethod, SaleChannel

NOT_GIVEN = "BELIRTILMEDI"


@dataclass(frozen=True)
class DaySale:
    id: int
    sale_no: str
    sold_at: datetime
    channel: SaleChannel
    customer_name: str
    seller_name: str
    payment_method: PaymentMethod | None
    amount: Decimal
    recall_violation: bool


@dataclass(frozen=True)
class DayTotal:
    key: str  # ödeme türü ya da satıcı adı
    sale_count: int
    amount: Decimal


@dataclass(frozen=True)
class DayReturn:
    return_no: str
    sale_no: str
    customer_name: str
    lot_no: str
    qty: Decimal
    refund_amount: Decimal


@dataclass(frozen=True)
class StockLeft:
    lot_no: str
    product_name: str
    base_unit: BaseUnit
    expiry_date: date | None
    qty: Decimal


@dataclass(frozen=True)
class DayEnd:
    day: date
    sale_count: int
    sales_amount: Decimal
    cost_amount: Decimal
    refund_amount: Decimal
    net_amount: Decimal
    by_payment: list[DayTotal]
    by_seller: list[DayTotal]
    sales: list[DaySale]
    returns: list[DayReturn]
    stock_left: list[StockLeft]  # yalnız tek bir depo (araç) istendiğinde


def day_end(
    session: Session,
    day: date,
    *,
    user_id: int | None = None,
    warehouse_id: int | None = None,
) -> DayEnd:
    start, end = business_day_bounds_utc(day)
    query = (
        select(Sale, Partner.name, User.full_name)
        .join(Partner, Partner.id == Sale.customer_id)
        .join(User, User.id == Sale.user_id)
        .where(Sale.sold_at >= start, Sale.sold_at < end)
        .order_by(Sale.sold_at, Sale.id)
    )
    if user_id is not None:
        query = query.where(Sale.user_id == user_id)
    if warehouse_id is not None:
        query = query.where(Sale.warehouse_id == warehouse_id)
    rows = session.execute(query).all()
    sale_ids = [sale.id for sale, _, _ in rows]
    amounts: dict[int, Decimal] = defaultdict(lambda: Decimal("0.00"))
    costs = Decimal("0.00")
    if sale_ids:
        for sale_id, amount, cost in session.execute(
            select(SaleLine.sale_id, SaleLine.amount, SaleLine.cost_amount).where(
                SaleLine.sale_id.in_(sale_ids)
            )
        ):
            amounts[sale_id] += amount
            costs += cost

    sales = [
        DaySale(
            id=sale.id,
            sale_no=sale.sale_no,
            sold_at=sale.sold_at,
            channel=sale.channel,
            customer_name=customer,
            seller_name=seller,
            payment_method=sale.payment_method,
            amount=amounts[sale.id],
            recall_violation=sale.recall_violation,
        )
        for sale, customer, seller in rows
    ]
    returns = _returns(session, start, end, user_id=user_id, warehouse_id=warehouse_id)
    sales_amount = sum((s.amount for s in sales), Decimal("0.00"))
    refund_amount = sum((r.refund_amount for r in returns), Decimal("0.00"))
    return DayEnd(
        day=day,
        sale_count=len(sales),
        sales_amount=sales_amount,
        cost_amount=costs,
        refund_amount=refund_amount,
        net_amount=sales_amount - refund_amount,
        by_payment=_totals(sales, lambda s: s.payment_method or NOT_GIVEN),
        by_seller=_totals(sales, lambda s: s.seller_name),
        sales=sales,
        returns=returns,
        stock_left=_stock_left(session, warehouse_id) if warehouse_id is not None else [],
    )


def _totals(sales: list[DaySale], key_of: Callable[[DaySale], str]) -> list[DayTotal]:
    counts: dict[str, int] = defaultdict(int)
    amounts: dict[str, Decimal] = defaultdict(lambda: Decimal("0.00"))
    for sale in sales:
        key = key_of(sale)
        counts[key] += 1
        amounts[key] += sale.amount
    return [DayTotal(key=key, sale_count=counts[key], amount=amounts[key]) for key in sorted(counts)]


def _returns(
    session: Session, start: datetime, end: datetime, *, user_id: int | None, warehouse_id: int | None
) -> list[DayReturn]:
    reversed_ids = select(StockMovement.reversal_of_id).where(StockMovement.reversal_of_id.is_not(None))
    query = (
        select(CustomerReturn, Sale.sale_no, Partner.name, Lot.lot_no, SaleLine.unit_price)
        .join(SaleLine, SaleLine.id == CustomerReturn.sale_line_id)
        .join(Sale, Sale.id == SaleLine.sale_id)
        .join(Partner, Partner.id == Sale.customer_id)
        .join(Lot, Lot.id == SaleLine.lot_id)
        .where(
            CustomerReturn.created_at >= start,
            CustomerReturn.created_at < end,
            CustomerReturn.stock_movement_id.not_in(reversed_ids),
        )
        .order_by(CustomerReturn.id)
    )
    if user_id is not None:
        query = query.where(Sale.user_id == user_id)
    if warehouse_id is not None:
        query = query.where(Sale.warehouse_id == warehouse_id)
    return [
        DayReturn(
            return_no=record.return_no,
            sale_no=sale_no,
            customer_name=customer,
            lot_no=lot_no,
            qty=record.qty,
            refund_amount=round_money(record.qty * unit_price),
        )
        for record, sale_no, customer, lot_no, unit_price in session.execute(query)
    ]


def _stock_left(session: Session, warehouse_id: int) -> list[StockLeft]:
    rows = session.execute(
        select(StockBalance.qty, Lot.lot_no, Lot.expiry_date, Product.name, Product.base_unit)
        .join(Lot, Lot.id == StockBalance.lot_id)
        .join(Product, Product.id == Lot.product_id)
        .where(StockBalance.warehouse_id == warehouse_id, StockBalance.qty > 0)
        .order_by(Product.name, Lot.expiry_date, Lot.lot_no)
    ).all()
    return [
        StockLeft(lot_no=lot_no, product_name=name, base_unit=unit, expiry_date=expiry, qty=qty)
        for qty, lot_no, expiry, name, unit in rows
    ]
