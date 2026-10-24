"""Ortak sütun tipleri ve karışımlar (ADR-006: hiçbir sütunda kayan noktalı tip yok)."""

from datetime import UTC, datetime
from enum import StrEnum

from sqlalchemy import BigInteger, DateTime, Enum, ForeignKey, Numeric
from sqlalchemy.dialects import mysql
from sqlalchemy.orm import Mapped, mapped_column

MONEY = Numeric(14, 2)  # defter tutarı (kuruş)
PRICE = Numeric(14, 4)  # birim fiyat / ücret
UNIT_COST = Numeric(14, 6)  # birim maliyet (yalnız bilgi ve gösterim)
QTY = Numeric(12, 3)  # miktar, ürünün temel biriminde (kg veya adet)
RATIO = Numeric(6, 4)  # oran, 0–1
TIMESTAMP = DateTime().with_variant(mysql.DATETIME(fsp=6), "mysql")


def utcnow() -> datetime:
    """Zamanlar veritabanında saat dilimsiz UTC olarak tutulur."""
    return datetime.now(UTC).replace(tzinfo=None)


def db_enum(enum_cls: type[StrEnum]) -> Enum:
    return Enum(enum_cls, native_enum=True, validate_strings=True)


class IdMixin:
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)


class AuditMixin:
    """Belge tablolarında kim ve ne zaman (NFR-008)."""

    created_at: Mapped[datetime] = mapped_column(TIMESTAMP, default=utcnow)
    created_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"))


class SyncMixin:
    """Android'e senkronize edilen tablolar: değişiklik numarası (architecture.md §5)."""

    change_seq: Mapped[int] = mapped_column(BigInteger, default=0, index=True)
