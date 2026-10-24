"""Depo transferi belgesi: her satır için defterde çıkış + giriş (değer taşımaz; ADR-008)."""

from collections.abc import Sequence
from dataclasses import dataclass
from decimal import Decimal

from sqlalchemy.orm import Session

from app.errors import InvalidInput
from app.models import Transfer, TransferLine, Warehouse
from app.models.enums import TransferReason
from app.models.types import utcnow
from app.services.ledger import post_transfer
from app.services.lookups import get_or_404
from app.services.numbering import next_document_no


@dataclass(frozen=True)
class TransferLineInput:
    lot_id: int
    qty: Decimal


def create_transfer(
    session: Session,
    *,
    from_warehouse_id: int,
    to_warehouse_id: int,
    lines: Sequence[TransferLineInput],
    reason: TransferReason,
    production_order_id: int | None = None,
    user_id: int | None = None,
) -> Transfer:
    get_or_404(session, Warehouse, from_warehouse_id, "Çıkış deposu")
    get_or_404(session, Warehouse, to_warehouse_id, "Giriş deposu")
    if not lines:
        raise InvalidInput("Transferde en az bir satır olmalı.")
    if len({line.lot_id for line in lines}) != len(lines):
        raise InvalidInput("Bir lot transferde yalnız bir kez yer alabilir.")

    transfer = Transfer(
        transfer_no=next_document_no(session, "TRF", utcnow().year),
        from_warehouse_id=from_warehouse_id,
        to_warehouse_id=to_warehouse_id,
        reason=reason,
        production_order_id=production_order_id,
        created_by=user_id,
    )
    session.add(transfer)
    session.flush()
    for line in lines:
        out, into = post_transfer(
            session,
            lot_id=line.lot_id,
            from_warehouse_id=from_warehouse_id,
            to_warehouse_id=to_warehouse_id,
            qty=line.qty,
            doc_id=transfer.id,
            user_id=user_id,
        )
        session.add(
            TransferLine(
                transfer_id=transfer.id,
                lot_id=line.lot_id,
                qty=line.qty,
                out_movement_id=out.id,
                in_movement_id=into.id,
            )
        )
    session.flush()
    return transfer
