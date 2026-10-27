"""Müşteri iadesi ve ikinci kademe dağıtım (FR-303, FR-308).

İade: satılan lot aynı lot numarasıyla depoya geri girer (IADE_GIRIS). Değeri, satış satırının
maliyetinin iade edilen paya düşen kısmıdır; satırın son iadesi kalan kuruşları alır, böylece bir satır
tamamen iade edildiğinde lota dönen değer satışta çıkan değere tam eşit olur. Bloke lota iade
kabul edilir: geri çağırmada mal müşteriden bu yolla geri toplanır.

İkinci kademe: müşterinin kendi alıcılarına teslimatı. Bizim stokumuzu etkilemez; yalnız izleme
listesinde "kesin" bilgi olarak görünür. Toplamı müşteride kalan miktarı aşamaz.
"""

from datetime import date
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.money import round_money, tr_number
from app.errors import InvalidInput
from app.models import CustomerReturn, OnwardDelivery, Partner, SaleLine, StockMovement
from app.models.enums import DocType, MovementType
from app.models.types import utcnow
from app.services.ledger import post_movement
from app.services.lookups import get_or_404, main_warehouse, warehouse_or_404
from app.services.numbering import next_document_no
from app.services.trace import returned_qty_by_line


def create_return(
    session: Session,
    *,
    sale_line_id: int,
    qty: Decimal,
    warehouse_id: int | None = None,
    reason: str | None = None,
    user_id: int | None = None,
) -> CustomerReturn:
    line = _lock_line(session, sale_line_id)
    if qty <= 0:
        raise InvalidInput("İade miktarı sıfırdan büyük olmalı.")
    already = returned_qty_by_line(session, [line.id]).get(line.id, Decimal(0))
    open_qty = line.qty - already
    if qty > open_qty:
        raise InvalidInput(
            f"Bu satırdan en fazla {tr_number(open_qty)} iade alınabilir "
            f"(satılan {tr_number(line.qty)}, önceki iadeler {tr_number(already)}).",
            available=open_qty,
            requested=qty,
        )
    onward = _onward_total(session, line.id)
    if onward > open_qty - qty:
        raise InvalidInput(
            f"Müşteri bu satırdan {tr_number(onward)} birimin kendi alıcılarına gittiğini bildirmiş; "
            f"en fazla {tr_number(open_qty - onward)} iade alınabilir. "
            "Önce müşterinin dağıtım kaydını düzeltin.",
            available=open_qty - onward,
            requested=qty,
        )
    if qty == open_qty:
        value = line.cost_amount - _returned_value(session, line.id)
    else:
        value = round_money(line.cost_amount * qty / line.qty)

    target = (
        warehouse_or_404(session, warehouse_id).id if warehouse_id is not None else main_warehouse(session).id
    )
    # Hareket, belge kimliği olarak iade kaydının kimliğini taşır: önce kayıt, sonra hareket ve bağı.
    record = CustomerReturn(
        return_no=next_document_no(session, "IAD", utcnow().year),
        sale_line_id=line.id,
        qty=qty,
        warehouse_id=target,
        reason=(reason or "").strip() or None,
        created_by=user_id,
    )
    session.add(record)
    session.flush()
    movement = post_movement(
        session,
        lot_id=line.lot_id,
        warehouse_id=target,
        movement_type=MovementType.IADE_GIRIS,
        qty=qty,
        value=value,
        doc_type=DocType.IADE,
        doc_id=record.id,
        user_id=user_id,
        note=record.reason,
    )
    record.stock_movement_id = movement.id
    session.flush()
    return record


def add_onward_delivery(
    session: Session,
    *,
    sale_line_id: int,
    recipient_partner_id: int,
    qty: Decimal,
    delivered_at: date | None = None,
    source_note: str | None = None,
    user_id: int | None = None,
) -> OnwardDelivery:
    line = _lock_line(session, sale_line_id)
    get_or_404(session, Partner, recipient_partner_id, "Alıcı")
    if qty <= 0:
        raise InvalidInput("Teslim miktarı sıfırdan büyük olmalı.")
    held = line.qty - returned_qty_by_line(session, [line.id]).get(line.id, Decimal(0))
    known = _onward_total(session, line.id)
    if known + qty > held:
        raise InvalidInput(
            f"Müşteride {tr_number(held)} kaldı; kayıtlı ikinci kademe teslimatlar "
            f"{tr_number(known)}. En fazla {tr_number(held - known)} eklenebilir.",
            available=held - known,
            requested=qty,
        )
    delivery = OnwardDelivery(
        sale_line_id=line.id,
        recipient_partner_id=recipient_partner_id,
        qty=qty,
        delivered_at=delivered_at,
        source_note=(source_note or "").strip() or None,
        created_by=user_id,
    )
    session.add(delivery)
    session.flush()
    return delivery


def _lock_line(session: Session, sale_line_id: int) -> SaleLine:
    """Aynı satıra aynı anda iki iade/dağıtım girilirse ikincisi birincinin sonucunu görsün."""
    line = session.execute(
        select(SaleLine)
        .where(SaleLine.id == sale_line_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    ).scalar_one_or_none()
    if line is None:
        get_or_404(session, SaleLine, sale_line_id, "Satış satırı")
    assert line is not None
    return line


def _onward_total(session: Session, sale_line_id: int) -> Decimal:
    values = session.scalars(
        select(OnwardDelivery.qty).where(OnwardDelivery.sale_line_id == sale_line_id)
    ).all()
    return sum(values, Decimal(0))


def _returned_value(session: Session, sale_line_id: int) -> Decimal:
    """Satırın geçerli (ters kayıtla geri alınmamış) iadelerinin lota dönen değeri."""
    reversed_ids = select(StockMovement.reversal_of_id).where(StockMovement.reversal_of_id.is_not(None))
    values = session.scalars(
        select(StockMovement.value)
        .join(CustomerReturn, CustomerReturn.stock_movement_id == StockMovement.id)
        .where(CustomerReturn.sale_line_id == sale_line_id, StockMovement.id.not_in(reversed_ids))
    ).all()
    return sum(values, Decimal(0))
