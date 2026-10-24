"""Alış (data_model.md §2.3)."""

from datetime import date
from decimal import Decimal

from sqlalchemy import CheckConstraint, Date, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base
from app.models.enums import PurchaseCostKind
from app.models.types import MONEY, PRICE, QTY, AuditMixin, IdMixin, db_enum


class Purchase(IdMixin, AuditMixin, Base):
    __tablename__ = "purchases"
    __table_args__ = (UniqueConstraint("supplier_id", "doc_no"),)

    doc_no: Mapped[str] = mapped_column(String(50))
    supplier_id: Mapped[int] = mapped_column(ForeignKey("partners.id"))
    doc_date: Mapped[date] = mapped_column(Date)
    note: Mapped[str | None] = mapped_column(String(255))


class PurchaseLine(IdMixin, Base):
    __tablename__ = "purchase_lines"
    __table_args__ = (
        CheckConstraint("qty > 0", name="qty_positive"),
        CheckConstraint("unit_price >= 0 AND invoice_amount >= 0", name="amounts_nonnegative"),
        # FR-207: fatura tutarı miktar × fiyattan farklıysa açıklama zorunlu
        CheckConstraint(
            "computed_amount = invoice_amount OR discrepancy_note IS NOT NULL", name="mismatch_needs_note"
        ),
    )

    purchase_id: Mapped[int] = mapped_column(ForeignKey("purchases.id"))
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"))
    lot_id: Mapped[int] = mapped_column(ForeignKey("lots.id"), unique=True)
    qty: Mapped[Decimal] = mapped_column(QTY)
    unit_price: Mapped[Decimal] = mapped_column(PRICE)
    computed_amount: Mapped[Decimal] = mapped_column(MONEY)  # kuruşa yuvarlanmış qty × unit_price
    invoice_amount: Mapped[Decimal] = mapped_column(MONEY)
    discrepancy_note: Mapped[str | None] = mapped_column(String(500))
    expiry_date: Mapped[date | None] = mapped_column(Date)


class PurchaseCost(IdMixin, Base):
    """Ek maliyet kalemleri; lot değeri = fatura tutarı + bunların toplamı."""

    __tablename__ = "purchase_costs"
    __table_args__ = (CheckConstraint("amount >= 0", name="amount_nonnegative"),)

    purchase_line_id: Mapped[int] = mapped_column(ForeignKey("purchase_lines.id"))
    kind: Mapped[PurchaseCostKind] = mapped_column(db_enum(PurchaseCostKind))
    amount: Mapped[Decimal] = mapped_column(MONEY)
    note: Mapped[str | None] = mapped_column(String(255))
