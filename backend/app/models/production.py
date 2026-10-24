"""Dış üretim ve yeniden işleme (data_model.md §2.4)."""

from datetime import datetime
from decimal import Decimal

from sqlalchemy import CheckConstraint, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base
from app.models.enums import ProductionKind, ProductionStatus
from app.models.types import MONEY, PRICE, QTY, TIMESTAMP, AuditMixin, IdMixin, db_enum, utcnow


class ProductionOrder(IdMixin, AuditMixin, Base):
    __tablename__ = "production_orders"
    __table_args__ = (
        CheckConstraint(
            "kind <> 'DIS_URETIM' OR "
            "(subcontractor_id IS NOT NULL AND subcontractor_warehouse_id IS NOT NULL)",
            name="external_needs_subcontractor",
        ),
        CheckConstraint("planned_qty > 0", name="planned_qty_positive"),
    )

    order_no: Mapped[str] = mapped_column(String(30), unique=True)
    kind: Mapped[ProductionKind] = mapped_column(db_enum(ProductionKind))
    subcontractor_id: Mapped[int | None] = mapped_column(ForeignKey("partners.id"))
    subcontractor_warehouse_id: Mapped[int | None] = mapped_column(ForeignKey("warehouses.id"))
    output_product_id: Mapped[int] = mapped_column(ForeignKey("products.id"))
    planned_qty: Mapped[Decimal] = mapped_column(QTY)
    status: Mapped[ProductionStatus] = mapped_column(
        db_enum(ProductionStatus), default=ProductionStatus.TASLAK
    )
    service_unit_price: Mapped[Decimal | None] = mapped_column(PRICE)
    service_invoice_no: Mapped[str | None] = mapped_column(String(50))
    service_amount: Mapped[Decimal | None] = mapped_column(MONEY)
    service_note: Mapped[str | None] = mapped_column(String(500))  # fatura ≠ adet × ücret ise açıklama
    received_qty: Mapped[Decimal | None] = mapped_column(QTY)
    output_lot_id: Mapped[int | None] = mapped_column(ForeignKey("lots.id"), unique=True)
    ordered_at: Mapped[datetime] = mapped_column(TIMESTAMP, default=utcnow)
    shipped_at: Mapped[datetime | None] = mapped_column(TIMESTAMP)
    completed_at: Mapped[datetime | None] = mapped_column(TIMESTAMP)


class ProductionInput(IdMixin, Base):
    """Emrin girdi lotları; miktar farkları (FR-109) buradan okunur."""

    __tablename__ = "production_inputs"
    __table_args__ = (
        UniqueConstraint("order_id", "lot_id"),
        CheckConstraint(
            "planned_qty > 0 AND shipped_qty >= 0 AND consumed_qty >= 0 AND returned_qty >= 0",
            name="quantities_valid",
        ),
    )

    order_id: Mapped[int] = mapped_column(ForeignKey("production_orders.id"))
    lot_id: Mapped[int] = mapped_column(ForeignKey("lots.id"))
    planned_qty: Mapped[Decimal] = mapped_column(QTY)
    shipped_qty: Mapped[Decimal] = mapped_column(QTY, default=Decimal(0))
    consumed_qty: Mapped[Decimal] = mapped_column(QTY, default=Decimal(0))
    returned_qty: Mapped[Decimal] = mapped_column(QTY, default=Decimal(0))
