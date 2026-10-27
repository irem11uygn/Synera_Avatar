"""Kayıt bulma yardımcıları: bulunamazsa Türkçe mesajlı NotFound."""

from collections import defaultdict
from collections.abc import Iterable
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.errors import InvalidInput, NotFound
from app.models import (
    Adjustment,
    CustomerReturn,
    Cutting,
    Lot,
    ProductionOrder,
    Purchase,
    Sale,
    Transfer,
    Warehouse,
)
from app.models.enums import DocType, WarehouseKind

# Hareketin bağlı olduğu belge türü → belge numarası sütunu.
DOC_NUMBER: dict[DocType, Any] = {
    DocType.ALIS: Purchase.doc_no,
    DocType.TRANSFER: Transfer.transfer_no,
    DocType.URETIM: ProductionOrder.order_no,
    DocType.PARCALAMA: Cutting.cutting_no,
    DocType.SATIS: Sale.sale_no,
    DocType.IADE: CustomerReturn.return_no,
    DocType.DUZELTME: Adjustment.adj_no,
}


def get_or_404[T](session: Session, model: type[T], entity_id: int, label: str) -> T:
    entity = session.get(model, entity_id)
    if entity is None:
        raise NotFound(f"{label} bulunamadı.", id=entity_id)
    return entity


def lot_by_no(session: Session, lot_no: str) -> Lot:
    lot = session.scalars(select(Lot).where(Lot.lot_no == lot_no)).one_or_none()
    if lot is None:
        raise NotFound(f"{lot_no} lotu bulunamadı.", lot_no=lot_no)
    return lot


def warehouse_or_404(session: Session, warehouse_id: int) -> Warehouse:
    """İstemcinin gönderdiği depo kimliği gerçekten var mı (yoksa veritabanı FK hatası yerine 404)."""
    warehouse = session.get(Warehouse, warehouse_id)
    if warehouse is None:
        raise NotFound("Depo bulunamadı.", warehouse_id=warehouse_id)
    return warehouse


def main_warehouse(session: Session) -> Warehouse:
    """Ana depo (sistemde tek ana depo varsayımı; data_model.md)."""
    warehouse = session.scalars(select(Warehouse).where(Warehouse.kind == WarehouseKind.ANA)).first()
    if warehouse is None:
        raise InvalidInput("Ana depo tanımlı değil.")
    return warehouse


def document_numbers(session: Session, refs: Iterable[tuple[DocType, int]]) -> dict[tuple[DocType, int], str]:
    """(belge türü, belge kimliği) çiftlerinin numaraları; her belge türü için tek sorgu."""
    wanted: dict[DocType, set[int]] = defaultdict(set)
    for doc_type, doc_id in refs:
        wanted[doc_type].add(doc_id)
    numbers: dict[tuple[DocType, int], str] = {}
    for doc_type, ids in wanted.items():
        column = DOC_NUMBER[doc_type]
        model = column.class_
        for doc_id, number in session.execute(select(model.id, column).where(model.id.in_(ids))):
            numbers[(doc_type, doc_id)] = number
    return numbers
