"""Depo transferi ve stok firesi (data_model.md §2.7)."""

from datetime import datetime
from decimal import Decimal

from sqlalchemy import CheckConstraint, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base
from app.models.enums import AdjustmentKind, TransferReason
from app.models.types import QTY, TIMESTAMP, AuditMixin, IdMixin, db_enum, utcnow


class Transfer(IdMixin, AuditMixin, Base):
    __tablename__ = "transfers"
    __table_args__ = (CheckConstraint("from_warehouse_id <> to_warehouse_id", name="different_warehouses"),)

    transfer_no: Mapped[str] = mapped_column(String(30), unique=True)
    from_warehouse_id: Mapped[int] = mapped_column(ForeignKey("warehouses.id"))
    to_warehouse_id: Mapped[int] = mapped_column(ForeignKey("warehouses.id"))
    reason: Mapped[TransferReason] = mapped_column(db_enum(TransferReason))
    production_order_id: Mapped[int | None] = mapped_column(ForeignKey("production_orders.id"))
    transferred_at: Mapped[datetime] = mapped_column(TIMESTAMP, default=utcnow)


class TransferLine(IdMixin, Base):
    __tablename__ = "transfer_lines"
    __table_args__ = (CheckConstraint("qty > 0", name="qty_positive"),)

    transfer_id: Mapped[int] = mapped_column(ForeignKey("transfers.id"))
    lot_id: Mapped[int] = mapped_column(ForeignKey("lots.id"))
    qty: Mapped[Decimal] = mapped_column(QTY)
    out_movement_id: Mapped[int] = mapped_column(ForeignKey("stock_movements.id"), unique=True)
    in_movement_id: Mapped[int] = mapped_column(ForeignKey("stock_movements.id"), unique=True)


class Adjustment(IdMixin, AuditMixin, Base):
    """Stoktaki malın firesi/imhası (işlem firesi cutting_outputs'ta durur)."""

    __tablename__ = "adjustments"
    __table_args__ = (CheckConstraint("qty > 0", name="qty_positive"),)

    adj_no: Mapped[str] = mapped_column(String(30), unique=True)
    kind: Mapped[AdjustmentKind] = mapped_column(db_enum(AdjustmentKind))
    lot_id: Mapped[int] = mapped_column(ForeignKey("lots.id"))
    warehouse_id: Mapped[int] = mapped_column(ForeignKey("warehouses.id"))
    qty: Mapped[Decimal] = mapped_column(QTY)
    reason: Mapped[str] = mapped_column(String(255))
    stock_movement_id: Mapped[int | None] = mapped_column(ForeignKey("stock_movements.id"), unique=True)


class StockCount(IdMixin, AuditMixin, Base):
    """Depo ya da araç sayımı: sayılan miktar ile defterdeki bakiye karşılaştırılır."""

    __tablename__ = "stock_counts"

    count_no: Mapped[str] = mapped_column(String(30), unique=True)
    warehouse_id: Mapped[int] = mapped_column(ForeignKey("warehouses.id"))
    note: Mapped[str | None] = mapped_column(String(255))


class StockCountLine(IdMixin, Base):
    """Eksik çıkan miktar fire kaydıyla düşülür (adjustment_id); fazlası yalnız raporlanır."""

    __tablename__ = "stock_count_lines"
    __table_args__ = (CheckConstraint("counted_qty >= 0", name="counted_qty_nonnegative"),)

    count_id: Mapped[int] = mapped_column(ForeignKey("stock_counts.id"))
    lot_id: Mapped[int] = mapped_column(ForeignKey("lots.id"))
    system_qty: Mapped[Decimal] = mapped_column(QTY)
    counted_qty: Mapped[Decimal] = mapped_column(QTY)
    adjustment_id: Mapped[int | None] = mapped_column(ForeignKey("adjustments.id"), unique=True)
