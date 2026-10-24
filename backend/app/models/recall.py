"""Geri çağırma ve uyarılar (data_model.md §2.8)."""

from datetime import datetime

from sqlalchemy import BigInteger, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base
from app.models.enums import AlertKind, RecallResolution, RecallStatus
from app.models.types import TIMESTAMP, IdMixin, db_enum, utcnow


class Recall(IdMixin, Base):
    __tablename__ = "recalls"

    recall_no: Mapped[str] = mapped_column(String(30), unique=True)
    source_lot_id: Mapped[int] = mapped_column(ForeignKey("lots.id"))
    reason: Mapped[str] = mapped_column(String(500))
    status: Mapped[RecallStatus] = mapped_column(db_enum(RecallStatus), default=RecallStatus.ACIK)
    resolution: Mapped[RecallResolution | None] = mapped_column(db_enum(RecallResolution))
    started_at: Mapped[datetime] = mapped_column(TIMESTAMP, default=utcnow)
    started_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    closed_at: Mapped[datetime | None] = mapped_column(TIMESTAMP)
    close_note: Mapped[str | None] = mapped_column(String(500))


class RecallLot(Base):
    """Başlatma anında etkilenen lotlar (bloke edilenler)."""

    __tablename__ = "recall_lots"

    recall_id: Mapped[int] = mapped_column(ForeignKey("recalls.id"), primary_key=True)
    lot_id: Mapped[int] = mapped_column(ForeignKey("lots.id"), primary_key=True)
    depth: Mapped[int] = mapped_column(Integer)


class Alert(IdMixin, Base):
    __tablename__ = "alerts"

    kind: Mapped[AlertKind] = mapped_column(db_enum(AlertKind))
    ref_type: Mapped[str] = mapped_column(String(30))
    ref_id: Mapped[int] = mapped_column(BigInteger)
    message: Mapped[str] = mapped_column(String(500))
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP, default=utcnow)
    acknowledged_at: Mapped[datetime | None] = mapped_column(TIMESTAMP)
