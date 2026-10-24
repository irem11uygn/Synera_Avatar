"""Kayıt bulma yardımcıları: bulunamazsa Türkçe mesajlı NotFound."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.errors import InvalidInput, NotFound
from app.models import Lot, Warehouse
from app.models.enums import WarehouseKind


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


def main_warehouse(session: Session) -> Warehouse:
    """Ana depo (sistemde tek ana depo varsayımı; data_model.md)."""
    warehouse = session.scalars(select(Warehouse).where(Warehouse.kind == WarehouseKind.ANA)).first()
    if warehouse is None:
        raise InvalidInput("Ana depo tanımlı değil.")
    return warehouse
