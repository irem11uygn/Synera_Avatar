"""Yeniden işleme (FR-302, FR-303): işletme içinde lotlardan yeni lot üretmek.

Örnek: müşteriden iade gelen sucuğun yeniden paketlenmesi, kısa tarihli parçaların kıymaya işlenmesi.
Dış üretimden farkı: sevk ve dış hizmet yoktur, işlem tek adımda tamamlanır. Kayıt yine bir üretim
emri olarak tutulur (tür YENIDEN_ISLEME, belge no YIS-…); defterde girdiler URETIM_TUKETIM, çıktı
URETIM_GIRIS hareketiyle yazılır ve lotlar YENIDEN_ISLEME bağıyla, miktarlarıyla bağlanır.
Çıktı lotunun değeri = tüketilen girdilerin değeri + ek maliyet (işçilik, ambalaj); bütünlük
kuralı I-6 bunu denetler. Bloke lot girdi olamaz (defter kuralı).
"""

from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.money import tr_number
from app.errors import InvalidInput
from app.models import Lot, Product, ProductionInput, ProductionOrder
from app.models.enums import (
    BaseUnit,
    DocType,
    LinkProcess,
    LotOrigin,
    MovementType,
    ProductionKind,
    ProductionStatus,
)
from app.models.types import utcnow
from app.services.ledger import create_lot, post_movement
from app.services.lookups import get_or_404, main_warehouse
from app.services.lot_graph import link_lots
from app.services.numbering import next_document_no


@dataclass(frozen=True)
class ReprocessInput:
    lot_id: int
    qty: Decimal


def reprocess(
    session: Session,
    *,
    inputs: list[ReprocessInput],
    output_product_id: int,
    output_qty: Decimal,
    extra_cost: Decimal = Decimal("0.00"),
    note: str | None = None,
    output_lot_no: str | None = None,
    warehouse_id: int | None = None,
    user_id: int | None = None,
) -> ProductionOrder:
    product = get_or_404(session, Product, output_product_id, "Çıktı ürünü")
    if output_qty <= 0:
        raise InvalidInput("Çıktı miktarı sıfırdan büyük olmalı.")
    if product.base_unit == BaseUnit.ADET and output_qty != output_qty.to_integral_value():
        raise InvalidInput(f"{product.name} adet ile izlenir; {tr_number(output_qty)} adet olamaz.")
    if extra_cost < 0:
        raise InvalidInput("Ek maliyet eksi olamaz.")
    if not inputs:
        raise InvalidInput("En az bir girdi lotu olmalı.")
    if len({i.lot_id for i in inputs}) != len(inputs):
        raise InvalidInput("Bir lot girdilerde yalnız bir kez yer alabilir.")
    for item in inputs:
        if item.qty <= 0:
            raise InvalidInput("Girdi miktarı sıfırdan büyük olmalı.")
    warehouse = warehouse_id if warehouse_id is not None else main_warehouse(session).id

    now = utcnow()
    order = ProductionOrder(
        order_no=next_document_no(session, "YIS", now.year),
        kind=ProductionKind.YENIDEN_ISLEME,
        output_product_id=product.id,
        planned_qty=output_qty,
        status=ProductionStatus.TAMAMLANDI,
        service_amount=extra_cost,
        service_note=(note or "").strip() or None,
        received_qty=output_qty,
        completed_at=now,
        created_by=user_id,
    )
    session.add(order)
    session.flush()

    consumed = Decimal(0)
    for item in inputs:
        movement = post_movement(
            session,
            lot_id=item.lot_id,
            warehouse_id=warehouse,
            movement_type=MovementType.URETIM_TUKETIM,
            qty=-item.qty,
            doc_type=DocType.URETIM,
            doc_id=order.id,
            user_id=user_id,
            note=order.service_note,
        )
        consumed -= movement.value
        session.add(
            ProductionInput(
                order_id=order.id,
                lot_id=item.lot_id,
                planned_qty=item.qty,
                shipped_qty=item.qty,
                consumed_qty=item.qty,
                returned_qty=Decimal(0),
            )
        )

    today = now.date()
    lot = create_lot(
        session,
        lot_no=output_lot_no or f"{product.lot_prefix or product.code}-{order.order_no}",
        product_id=product.id,
        origin=LotOrigin.YENIDEN_ISLEME,
        qty=output_qty,
        value=consumed + extra_cost,
        warehouse_id=warehouse,
        movement_type=MovementType.URETIM_GIRIS,
        doc_type=DocType.URETIM,
        doc_id=order.id,
        produced_at=today,
        expiry_date=_expiry(session, product, inputs, today),
        user_id=user_id,
    )
    for item in inputs:
        link_lots(
            session,
            parent_lot_id=item.lot_id,
            child_lot_id=lot.id,
            qty=item.qty,
            process=LinkProcess.YENIDEN_ISLEME,
            process_id=order.id,
        )
    order.output_lot_id = lot.id
    session.flush()
    return order


def _expiry(session: Session, product: Product, inputs: list[ReprocessInput], today: date) -> date | None:
    """Yeniden işlenen ürünün son kullanma tarihi girdilerin en erkeninden sonra olamaz."""
    own = today + timedelta(days=product.shelf_life_days) if product.shelf_life_days else None
    dates = [
        d
        for d in session.scalars(select(Lot.expiry_date).where(Lot.id.in_(i.lot_id for i in inputs)))
        if d is not None
    ]
    candidates = [d for d in (own, min(dates) if dates else None) if d is not None]
    return min(candidates) if candidates else None
