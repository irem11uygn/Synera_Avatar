"""Geri çağırma (FR-306, FR-307, FR-310) ve uyarılar.

Başlatma: kaynak lot ve ondan türeyen bütün lotlar (ileri izleme) tek işlemde BLOKE olur ve kayda
geçer. Bloke lot hiçbir kanaldan satılamaz, transfer edilemez, üretimde ya da parçalamada
kullanılamaz (defter kuralı). Lotun durumu değişince değişiklik numarası artar; Android bir sonraki
eşitlemede lotu bloke görür.

Liste: etkilenen lotlar, bizdeki stok, müşteri/market bazında miktar, satış belgeleri, iletişim ve
ikinci kademe bilgisi (izleme servisinden, kesin kayıtlarla). Geri çağırmadan sonra çevrimdışı satış
yapılmışsa o müşteri de listede ihlal işaretiyle görünür.

Kapatma: IMHA → bizdeki kalan stok fire/imha olarak düşülür, lotlar bloke kalır. SERBEST → başka
açık geri çağırmada olmayan lotlar yeniden satılabilir olur.
"""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.errors import InvalidInput, InvalidState
from app.models import Lot, Partner, Recall, RecallContact, RecallLot, StockBalance, User
from app.models.enums import ContactOutcome, LotStatus, RecallResolution, RecallStatus
from app.models.types import utcnow
from app.services.adjustments import create_adjustment
from app.services.lookups import get_or_404, lot_by_no
from app.services.lot_graph import descendants
from app.services.numbering import next_document_no
from app.services.quality import held_lot_ids
from app.services.trace import Recipient, StockItem, TracedLot, recipients_of, stock_of, traced_lots


def start_recall(session: Session, *, lot_no: str, reason: str, user_id: int | None = None) -> Recall:
    if not reason.strip():
        raise InvalidInput("Geri çağırma nedeni zorunlu.")
    source = lot_by_no(session, lot_no)
    # Aynı lot için aynı anda iki başlatma: ikincisi kilidi bekler ve birincinin kaydını görür.
    session.execute(select(Lot.id).where(Lot.id == source.id).with_for_update())
    existing = session.scalars(
        select(Recall).where(Recall.source_lot_id == source.id, Recall.status == RecallStatus.ACIK)
    ).first()
    if existing is not None:
        raise InvalidState(
            f"{source.lot_no} için açık bir geri çağırma zaten var: {existing.recall_no}.",
            recall_no=existing.recall_no,
        )
    recall = Recall(
        recall_no=next_document_no(session, "GC", utcnow().year),
        source_lot_id=source.id,
        reason=reason.strip(),
        started_by=user_id,
    )
    session.add(recall)
    session.flush()
    depths = descendants(session, source.id)
    lots = session.scalars(select(Lot).where(Lot.id.in_(depths)).with_for_update()).all()
    for lot in lots:
        lot.status = LotStatus.BLOKE
        session.add(RecallLot(recall_id=recall.id, lot_id=lot.id, depth=depths[lot.id]))
    session.flush()
    return recall


def close_recall(
    session: Session,
    recall_id: int,
    *,
    resolution: RecallResolution,
    note: str | None = None,
    user_id: int | None = None,
) -> Recall:
    recall = session.execute(
        select(Recall)
        .where(Recall.id == recall_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    ).scalar_one_or_none()
    if recall is None:
        get_or_404(session, Recall, recall_id, "Geri çağırma")
    assert recall is not None
    if recall.status != RecallStatus.ACIK:
        raise InvalidState(f"{recall.recall_no} zaten kapatılmış.", recall_no=recall.recall_no)
    lot_ids = list(session.scalars(select(RecallLot.lot_id).where(RecallLot.recall_id == recall.id)))

    if resolution == RecallResolution.IMHA:
        balances = session.execute(
            select(StockBalance.lot_id, StockBalance.warehouse_id, StockBalance.qty)
            .where(StockBalance.lot_id.in_(lot_ids), StockBalance.qty > 0)
            .order_by(StockBalance.lot_id, StockBalance.warehouse_id)
        ).all()
        for lot_id, warehouse_id, qty in balances:
            create_adjustment(
                session,
                lot_id=lot_id,
                warehouse_id=warehouse_id,
                qty=qty,
                reason=f"{recall.recall_no} geri çağırma: imha",
                user_id=user_id,
            )
    else:
        still_blocked = set(
            session.scalars(
                select(RecallLot.lot_id)
                .join(Recall, Recall.id == RecallLot.recall_id)
                .where(
                    RecallLot.lot_id.in_(lot_ids),
                    Recall.status == RecallStatus.ACIK,
                    Recall.id != recall.id,
                )
            )
        ) | held_lot_ids(session, lot_ids)  # açık kalite blokesindeki lot kapalı kalır
        for lot in session.scalars(select(Lot).where(Lot.id.in_(lot_ids)).with_for_update()):
            if lot.id not in still_blocked:
                lot.status = LotStatus.AKTIF

    recall.status = RecallStatus.KAPANDI
    recall.resolution = resolution
    recall.closed_at = utcnow()
    recall.close_note = (note or "").strip() or None
    session.flush()
    return recall


@dataclass(frozen=True)
class ContactView:
    id: int
    customer_id: int
    customer: str
    outcome: ContactOutcome
    note: str | None
    user_name: str | None
    created_at: datetime


REACHED = (ContactOutcome.ULASILDI, ContactOutcome.URUN_KALMADI)


@dataclass(frozen=True)
class RecallView:
    recall: Recall
    source_lot_no: str
    started_by_name: str | None
    lots: list[TracedLot]
    stock: list[StockItem]
    recipients: list[Recipient]
    contacts: list[ContactView]  # yeniden eskiye

    def latest_outcomes(self) -> dict[int, ContactOutcome]:
        """Müşteri başına son iletişim sonucu (kaydı olmayan müşteri listede yok = bekliyor)."""
        latest: dict[int, ContactOutcome] = {}
        for contact in self.contacts:
            latest.setdefault(contact.customer_id, contact.outcome)
        return latest

    def contact_counts(self) -> dict[str, int]:
        latest = self.latest_outcomes()
        customers = {r.customer_id for r in self.recipients}
        reached = sum(1 for c in customers if latest.get(c) in REACHED)
        unreached = sum(1 for c in customers if latest.get(c) == ContactOutcome.ULASILAMADI)
        return {"reached": reached, "unreached": unreached, "pending": len(customers) - reached - unreached}

    @property
    def customer_count(self) -> int:
        return len({r.customer_id for r in self.recipients})

    @property
    def violation_count(self) -> int:
        return sum(1 for r in self.recipients if r.recall_violation)


def recall_view(session: Session, recall: Recall) -> RecallView:
    rows = session.execute(select(RecallLot.lot_id, RecallLot.depth).where(RecallLot.recall_id == recall.id))
    depths = {lot_id: depth for lot_id, depth in rows}
    source = session.get(Lot, recall.source_lot_id)
    user = session.get(User, recall.started_by) if recall.started_by else None
    assert source is not None
    return RecallView(
        recall=recall,
        source_lot_no=source.lot_no,
        started_by_name=user.full_name if user else None,
        lots=traced_lots(session, depths),
        stock=stock_of(session, depths.keys()),
        recipients=recipients_of(session, depths.keys()),
        contacts=contacts_of(session, recall.id),
    )


def contacts_of(session: Session, recall_id: int) -> list[ContactView]:
    rows = session.execute(
        select(RecallContact, Partner.name, User.full_name)
        .join(Partner, Partner.id == RecallContact.partner_id)
        .outerjoin(User, User.id == RecallContact.user_id)
        .where(RecallContact.recall_id == recall_id)
        .order_by(RecallContact.id.desc())
    ).all()
    return [
        ContactView(c.id, c.partner_id, name, c.outcome, c.note, user_name, c.created_at)
        for c, name, user_name in rows
    ]


def add_contact(
    session: Session,
    recall: Recall,
    *,
    partner_id: int,
    outcome: ContactOutcome,
    note: str | None = None,
    user_id: int | None = None,
) -> RecallContact:
    """Müşteriyle iletişimi kaydeder (yalnız eklenir); yalnız açık geri çağırmada, etkilenen müşteriye."""
    if recall.status != RecallStatus.ACIK:
        raise InvalidState(
            f"{recall.recall_no} kapatılmış; iletişim kaydı eklenemez.", recall_no=recall.recall_no
        )
    lot_ids = list(session.scalars(select(RecallLot.lot_id).where(RecallLot.recall_id == recall.id)))
    if partner_id not in {r.customer_id for r in recipients_of(session, lot_ids)}:
        raise InvalidInput(
            "Bu müşteri bu geri çağırmadan etkilenen alıcılar arasında değil.", partner_id=partner_id
        )
    contact = RecallContact(
        recall_id=recall.id,
        partner_id=partner_id,
        outcome=outcome,
        note=(note or "").strip() or None,
        user_id=user_id,
    )
    session.add(contact)
    session.flush()
    return contact


def held_by_customers(view: RecallView) -> dict[str, Decimal]:
    """Müşterilerde kalan toplam miktar, birim başına (kg / adet)."""
    totals: dict[str, Decimal] = {}
    for recipient in view.recipients:
        totals[recipient.base_unit] = totals.get(recipient.base_unit, Decimal(0)) + recipient.qty
    return totals
