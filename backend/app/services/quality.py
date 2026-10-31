"""Kalite blokesi (karantina) — geri çağırmadan bağımsız.

Şüpheli bir lot soruşturma bitene kadar satışa ve kullanıma kapanır: lot durumu BLOKE olur, böylece web,
telefon (bir sonraki eşitlemede) ve stok defteri aynı kuralla engeller. Yalnız o lot kapanır; türeyen
lotlar için şüphe doğrulanınca geri çağırma başlatılır.

Blokeyi kaldırmak lotu ancak açık bir geri çağırmada değilse yeniden satışa açar; geri çağırma
"serbest bırak" ile kapanırken de açık kalite blokesindeki lot kapalı kalır (services/recall.py).
"""

from collections.abc import Iterable

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.errors import InvalidInput, InvalidState
from app.models import Lot, QualityHold, Recall, RecallLot, User
from app.models.enums import LotStatus, RecallStatus
from app.models.types import utcnow
from app.services.lookups import lot_by_no


def _locked_lot(session: Session, lot_no: str) -> Lot:
    lot = lot_by_no(session, lot_no)
    session.execute(select(Lot.id).where(Lot.id == lot.id).with_for_update())
    return lot


def active_hold(session: Session, lot_id: int) -> QualityHold | None:
    return session.scalars(
        select(QualityHold).where(QualityHold.lot_id == lot_id, QualityHold.released_at.is_(None))
    ).first()


def held_lot_ids(session: Session, lot_ids: Iterable[int]) -> set[int]:
    """Verilen lotlardan açık kalite blokesinde olanlar."""
    return set(
        session.scalars(
            select(QualityHold.lot_id).where(
                QualityHold.lot_id.in_(list(lot_ids)), QualityHold.released_at.is_(None)
            )
        )
    )


def open_recalls_of(session: Session, lot_id: int) -> list[str]:
    """Lotu kapsayan açık geri çağırmaların numaraları."""
    return list(
        session.scalars(
            select(Recall.recall_no)
            .join(RecallLot, RecallLot.recall_id == Recall.id)
            .where(RecallLot.lot_id == lot_id, Recall.status == RecallStatus.ACIK)
            .order_by(Recall.id)
        )
    )


def place_hold(session: Session, *, lot_no: str, reason: str, user: User) -> QualityHold:
    reason = reason.strip()
    if not reason:
        raise InvalidInput("Kalite blokesi nedeni zorunlu.")
    lot = _locked_lot(session, lot_no)
    if active_hold(session, lot.id) is not None:
        raise InvalidState(f"{lot.lot_no} zaten kalite blokesinde.", lot_no=lot.lot_no)
    hold = QualityHold(lot_id=lot.id, reason=reason, placed_by=user.id)
    session.add(hold)
    lot.status = LotStatus.BLOKE
    session.flush()
    return hold


def release_hold(
    session: Session, *, lot_no: str, note: str | None, user: User
) -> tuple[QualityHold, list[str]]:
    """Blokeyi kaldırır; ikinci değer lotu hâlâ kapalı tutan açık geri çağırmalar (boşsa satışa açıldı)."""
    lot = _locked_lot(session, lot_no)
    hold = active_hold(session, lot.id)
    if hold is None:
        raise InvalidState(f"{lot.lot_no} için açık kalite blokesi yok.", lot_no=lot.lot_no)
    hold.released_at = utcnow()
    hold.released_by = user.id
    hold.release_note = (note or "").strip() or None
    recalls = open_recalls_of(session, lot.id)
    if not recalls:
        lot.status = LotStatus.AKTIF
    session.flush()
    return hold, recalls


def holds_of(session: Session, lot_id: int) -> list[QualityHold]:
    """Lotun bütün kalite blokeleri, yeniden eskiye."""
    return list(
        session.scalars(
            select(QualityHold).where(QualityHold.lot_id == lot_id).order_by(QualityHold.id.desc())
        )
    )
