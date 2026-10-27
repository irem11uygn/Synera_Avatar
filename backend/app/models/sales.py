"""Satış, iade ve ikinci kademe dağıtım (data_model.md §2.6)."""

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import CheckConstraint, Date, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base
from app.models.enums import PaymentMethod, SaleChannel
from app.models.types import MONEY, PRICE, QTY, TIMESTAMP, AuditMixin, IdMixin, db_enum, utcnow


class Sale(IdMixin, Base):
    __tablename__ = "sales"

    client_uuid: Mapped[str] = mapped_column(String(36), unique=True)  # tekrar güvenlik anahtarı (AT-11)
    sale_no: Mapped[str] = mapped_column(String(30), unique=True)  # aynı zamanda teslim belgesi no
    channel: Mapped[SaleChannel] = mapped_column(db_enum(SaleChannel))
    customer_id: Mapped[int] = mapped_column(ForeignKey("partners.id"), index=True)
    warehouse_id: Mapped[int] = mapped_column(ForeignKey("warehouses.id"))
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    device_id: Mapped[str | None] = mapped_column(String(64))
    sold_at: Mapped[datetime] = mapped_column(TIMESTAMP)  # cihaz zamanı, yalnız bilgi
    received_at: Mapped[datetime] = mapped_column(TIMESTAMP, default=utcnow)
    recall_violation: Mapped[bool] = mapped_column(default=False)
    payment_method: Mapped[PaymentMethod | None] = mapped_column(db_enum(PaymentMethod))


class SaleLine(IdMixin, Base):
    """Bir satır = bir lot = bir stok hareketi (FR-401)."""

    __tablename__ = "sale_lines"
    __table_args__ = (
        UniqueConstraint("sale_id", "line_no"),
        CheckConstraint("qty > 0", name="qty_positive"),
    )

    sale_id: Mapped[int] = mapped_column(ForeignKey("sales.id"))
    line_no: Mapped[int] = mapped_column(Integer)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"))
    lot_id: Mapped[int] = mapped_column(ForeignKey("lots.id"), index=True)
    qty: Mapped[Decimal] = mapped_column(QTY)
    unit_price: Mapped[Decimal] = mapped_column(PRICE)
    amount: Mapped[Decimal] = mapped_column(MONEY)
    stock_movement_id: Mapped[int] = mapped_column(ForeignKey("stock_movements.id"), unique=True)
    cost_amount: Mapped[Decimal] = mapped_column(MONEY)  # hareketin değeri (brüt kâr için)


class CustomerReturn(IdMixin, AuditMixin, Base):
    __tablename__ = "customer_returns"
    __table_args__ = (CheckConstraint("qty > 0", name="qty_positive"),)

    return_no: Mapped[str] = mapped_column(String(30), unique=True)
    sale_line_id: Mapped[int] = mapped_column(ForeignKey("sale_lines.id"))
    qty: Mapped[Decimal] = mapped_column(QTY)
    warehouse_id: Mapped[int] = mapped_column(ForeignKey("warehouses.id"))
    reason: Mapped[str | None] = mapped_column(String(255))
    stock_movement_id: Mapped[int | None] = mapped_column(ForeignKey("stock_movements.id"), unique=True)


class OnwardDelivery(IdMixin, AuditMixin, Base):
    """Müşterinin kendi alıcılarına teslimatı (FR-308); bizim stokumuzu etkilemez."""

    __tablename__ = "onward_deliveries"
    __table_args__ = (CheckConstraint("qty > 0", name="qty_positive"),)

    sale_line_id: Mapped[int] = mapped_column(ForeignKey("sale_lines.id"))
    recipient_partner_id: Mapped[int] = mapped_column(ForeignKey("partners.id"))
    qty: Mapped[Decimal] = mapped_column(QTY)
    delivered_at: Mapped[date | None] = mapped_column(Date)
    source_note: Mapped[str | None] = mapped_column(String(255))
