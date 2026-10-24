"""Lot ağı: miktarlı bağlantı yazma ve ileri/geri gezinme (FR-302, FR-304, FR-305)."""

from collections.abc import Collection
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.graph import traverse
from app.errors import InvalidInput
from app.models import LotLink
from app.models.enums import LinkProcess


def link_lots(
    session: Session,
    *,
    parent_lot_id: int,
    child_lot_id: int,
    qty: Decimal,
    process: LinkProcess,
    process_id: int,
) -> LotLink:
    """Girdi lotunu çıktı lotuna, kullanılan miktarla bağlar."""
    if parent_lot_id == child_lot_id:
        raise InvalidInput("Bir lot kendisine bağlanamaz.", lot_id=parent_lot_id)
    if qty <= 0:
        raise InvalidInput("Bağlantı miktarı sıfırdan büyük olmalı.", qty=qty)
    link = LotLink(
        parent_lot_id=parent_lot_id,
        child_lot_id=child_lot_id,
        qty=qty,
        process=process,
        process_id=process_id,
    )
    session.add(link)
    session.flush()
    return link


def descendants(session: Session, lot_id: int) -> dict[int, int]:
    """İleri izleme: lot ve ondan türeyen bütün lotlar → derinlik."""

    def children(ids: Collection[int]) -> list[int]:
        return list(session.scalars(select(LotLink.child_lot_id).where(LotLink.parent_lot_id.in_(ids))))

    return traverse(lot_id, children)


def ancestors(session: Session, lot_id: int) -> dict[int, int]:
    """Geri izleme: lot ve onu oluşturan bütün lotlar → derinlik."""

    def parents(ids: Collection[int]) -> list[int]:
        return list(session.scalars(select(LotLink.parent_lot_id).where(LotLink.child_lot_id.in_(ids))))

    return traverse(lot_id, parents)
