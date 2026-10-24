"""Senkronizasyon değişiklik sayacı ve değişiklik numarasının otomatik atanması (architecture.md §5)."""

from typing import Any

from sqlalchemy import BigInteger, CheckConstraint, Connection, Integer, event, select, update
from sqlalchemy.orm import Mapped, Session, mapped_column

from app.db import Base
from app.models.types import SyncMixin


class SyncCounter(Base):
    """Tek satır; satır kilidi işlem bitene kadar tutulduğu için numaralar işlenme sırasıyla dağılır."""

    __tablename__ = "sync_counter"
    __table_args__ = (CheckConstraint("id = 1", name="single_row"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=False)
    value: Mapped[int] = mapped_column(BigInteger, default=0)


def next_change_seq(connection: Connection) -> int:
    current = connection.execute(
        select(SyncCounter.value).where(SyncCounter.id == 1).with_for_update()
    ).scalar_one()
    connection.execute(update(SyncCounter).where(SyncCounter.id == 1).values(value=current + 1))
    return current + 1


@event.listens_for(Session, "before_flush")
def _assign_change_seq(session: Session, _flush_context: Any, _instances: Any) -> None:
    """Senkronize edilen tablolarda eklenen/değişen her satıra yeni değişiklik numarası yazar."""
    changed = [
        obj
        for obj in (*session.new, *session.dirty)
        if isinstance(obj, SyncMixin) and (obj in session.new or session.is_modified(obj))
    ]
    if changed:
        seq = next_change_seq(session.connection())
        for obj in changed:
            obj.change_seq = seq
