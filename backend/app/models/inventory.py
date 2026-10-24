"""Lot, lot ağı, stok hareket defteri ve bakiyeler (data_model.md §2.2, ADR-008)."""

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import BigInteger, CheckConstraint, Date, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base
from app.models.enums import DocType, LinkProcess, LotOrigin, LotStatus, MovementType
from app.models.types import (
    MONEY,
    QTY,
    TIMESTAMP,
    UNIT_COST,
    AuditMixin,
    IdMixin,
    SyncMixin,
    db_enum,
    utcnow,
)


class Lot(IdMixin, AuditMixin, SyncMixin, Base):
    __tablename__ = "lots"
    __table_args__ = (
        CheckConstraint("initial_qty > 0", name="initial_qty_positive"),
        CheckConstraint("remaining_qty >= 0", name="remaining_qty_nonnegative"),
    )

    lot_no: Mapped[str] = mapped_column(String(40), unique=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"))
    origin: Mapped[LotOrigin] = mapped_column(db_enum(LotOrigin))
    supplier_id: Mapped[int | None] = mapped_column(ForeignKey("partners.id"))
    produced_at: Mapped[date | None] = mapped_column(Date)
    expiry_date: Mapped[date | None] = mapped_column(Date)
    status: Mapped[LotStatus] = mapped_column(db_enum(LotStatus), default=LotStatus.AKTIF)
    initial_qty: Mapped[Decimal] = mapped_column(QTY)
    initial_value: Mapped[Decimal] = mapped_column(MONEY)
    unit_cost: Mapped[Decimal] = mapped_column(UNIT_COST)  # initial_value / initial_qty, yalnız bilgi
    remaining_qty: Mapped[Decimal] = mapped_column(QTY)
    remaining_value: Mapped[Decimal] = mapped_column(MONEY)


class LotLink(IdMixin, Base):
    """Çoktan çoğa lot ilişkisi, miktarıyla (FR-302)."""

    __tablename__ = "lot_links"
    __table_args__ = (
        CheckConstraint("parent_lot_id <> child_lot_id", name="not_self"),
        CheckConstraint("qty > 0", name="qty_positive"),
    )

    parent_lot_id: Mapped[int] = mapped_column(ForeignKey("lots.id"), index=True)
    child_lot_id: Mapped[int] = mapped_column(ForeignKey("lots.id"), index=True)
    qty: Mapped[Decimal] = mapped_column(QTY)  # ebeveyn lottan bu çocuğa giden miktar
    process: Mapped[LinkProcess] = mapped_column(db_enum(LinkProcess))
    process_id: Mapped[int] = mapped_column(BigInteger)


class StockMovement(IdMixin, Base):
    """Yalnız eklenen defter: UPDATE ve DELETE MySQL tetikleyicileriyle engellenir."""

    __tablename__ = "stock_movements"
    __table_args__ = (
        CheckConstraint("qty <> 0", name="qty_nonzero"),
        Index("ix_stock_movements_doc", "doc_type", "doc_id"),
    )

    posted_at: Mapped[datetime] = mapped_column(TIMESTAMP, default=utcnow)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    type: Mapped[MovementType] = mapped_column(db_enum(MovementType))
    lot_id: Mapped[int] = mapped_column(ForeignKey("lots.id"), index=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"))
    warehouse_id: Mapped[int] = mapped_column(ForeignKey("warehouses.id"))
    qty: Mapped[Decimal] = mapped_column(QTY)  # işaretli: giriş +, çıkış −
    value: Mapped[Decimal] = mapped_column(MONEY)  # işaretli
    doc_type: Mapped[DocType] = mapped_column(db_enum(DocType))
    doc_id: Mapped[int] = mapped_column(BigInteger)
    reversal_of_id: Mapped[int | None] = mapped_column(ForeignKey("stock_movements.id"), unique=True)
    note: Mapped[str | None] = mapped_column(String(255))


class StockBalance(SyncMixin, Base):
    """Lot × depo bakiyesi; hareketle aynı işlemde güncellenir."""

    __tablename__ = "stock_balances"
    __table_args__ = (CheckConstraint("qty >= 0", name="qty_nonnegative"),)

    lot_id: Mapped[int] = mapped_column(ForeignKey("lots.id"), primary_key=True)
    warehouse_id: Mapped[int] = mapped_column(ForeignKey("warehouses.id"), primary_key=True)
    qty: Mapped[Decimal] = mapped_column(QTY, default=Decimal(0))
