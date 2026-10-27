"""Depo ve araç sayımı: sayılan miktar defterdeki bakiyeyle karşılaştırılır.

Eksik çıkan miktar fire kaydıyla ("Sayım farkı") düşülür; bakiye sayılan miktara iner. Fazla çıkan
miktar stoka eklenmez: kaynağı belirsiz mal deftere girmez, sayım belgesinde raporlanır ve araştırılır
(yanlış partiye yazılmış satış, eksik transfer...). Sayılmayan partiler değişmez (kısmi sayım).
"""

from collections.abc import Sequence
from dataclasses import dataclass
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.money import tr_number
from app.errors import Forbidden, InvalidInput
from app.models import Adjustment, Lot, Product, StockBalance, StockCount, StockCountLine, StockMovement, User
from app.models.enums import BaseUnit, UserRole
from app.models.types import utcnow
from app.services.adjustments import create_adjustment
from app.services.lookups import warehouse_or_404
from app.services.numbering import next_document_no


@dataclass(frozen=True)
class CountLineInput:
    lot_no: str
    counted_qty: Decimal


def record_count(
    session: Session,
    user: User,
    *,
    warehouse_id: int,
    lines: Sequence[CountLineInput],
    note: str | None = None,
) -> StockCount:
    warehouse_or_404(session, warehouse_id)
    if user.role == UserRole.SATIS and warehouse_id != user.warehouse_id:
        raise Forbidden("Satış elemanı yalnız kendi aracını sayabilir.")
    if not lines:
        raise InvalidInput("Sayımda en az bir parti olmalı.")
    lot_nos = [line.lot_no for line in lines]
    if len(set(lot_nos)) != len(lot_nos):
        raise InvalidInput("Aynı parti sayımda iki kez yazılmış.")

    count = StockCount(
        count_no=next_document_no(session, "SAY", utcnow().year),
        warehouse_id=warehouse_id,
        note=(note or "").strip() or None,
        created_by=user.id,
    )
    session.add(count)
    session.flush()
    for line in lines:
        if line.counted_qty < 0:
            raise InvalidInput(f"{line.lot_no}: sayılan miktar eksi olamaz.")
        lot = session.scalars(select(Lot).where(Lot.lot_no == line.lot_no)).first()
        if lot is None:
            raise InvalidInput(f"{line.lot_no} partisi bulunamadı.", lot_no=line.lot_no)
        product = session.get(Product, lot.product_id)
        assert product is not None
        if product.base_unit == BaseUnit.ADET and line.counted_qty != line.counted_qty.to_integral_value():
            raise InvalidInput(f"{product.name} adet ile sayılır; {tr_number(line.counted_qty)} adet olamaz.")
        balance = session.get(StockBalance, (lot.id, warehouse_id))
        system_qty = balance.qty if balance is not None else Decimal(0)
        adjustment_id = None
        if line.counted_qty < system_qty:
            adjustment = create_adjustment(
                session,
                lot_id=lot.id,
                warehouse_id=warehouse_id,
                qty=system_qty - line.counted_qty,
                reason=f"Sayım farkı ({count.count_no})",
                user_id=user.id,
            )
            adjustment_id = adjustment.id
        session.add(
            StockCountLine(
                count_id=count.id,
                lot_id=lot.id,
                system_qty=system_qty,
                counted_qty=line.counted_qty,
                adjustment_id=adjustment_id,
            )
        )
    session.flush()
    return count


@dataclass(frozen=True)
class CountLineView:
    lot_no: str
    product_name: str
    base_unit: BaseUnit
    system_qty: Decimal
    counted_qty: Decimal
    difference: Decimal  # sayılan − defter; eksi: eksik (fire yazıldı), artı: fazla (araştırılmalı)
    shortage_value: Decimal  # eksik çıkan malın maliyeti (fire kaydının değeri)


def count_lines(session: Session, count: StockCount) -> list[CountLineView]:
    rows = session.execute(
        select(StockCountLine, Lot.lot_no, Product.name, Product.base_unit, StockMovement.value)
        .join(Lot, Lot.id == StockCountLine.lot_id)
        .join(Product, Product.id == Lot.product_id)
        .outerjoin(Adjustment, Adjustment.id == StockCountLine.adjustment_id)
        .outerjoin(StockMovement, StockMovement.id == Adjustment.stock_movement_id)
        .where(StockCountLine.count_id == count.id)
        .order_by(StockCountLine.id)
    ).all()
    return [
        CountLineView(
            lot_no=lot_no,
            product_name=name,
            base_unit=unit,
            system_qty=line.system_qty,
            counted_qty=line.counted_qty,
            difference=line.counted_qty - line.system_qty,
            shortage_value=-value if value is not None else Decimal("0.00"),
        )
        for line, lot_no, name, unit, value in rows
    ]
