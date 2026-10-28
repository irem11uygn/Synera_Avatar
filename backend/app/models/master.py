"""Ana veriler ve kullanıcılar (data_model.md §2.1)."""

from datetime import datetime
from decimal import Decimal

from sqlalchemy import CheckConstraint, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base
from app.models.enums import BaseUnit, ProductKind, UserRole, WarehouseKind
from app.models.types import MONEY, PRICE, QTY, TIMESTAMP, IdMixin, SyncMixin, db_enum, utcnow


class User(IdMixin, Base):
    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint("role <> 'SATIS' OR warehouse_id IS NOT NULL", name="satis_needs_warehouse"),
    )

    username: Mapped[str] = mapped_column(String(50), unique=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    full_name: Mapped[str] = mapped_column(String(100))
    role: Mapped[UserRole] = mapped_column(db_enum(UserRole))
    warehouse_id: Mapped[int | None] = mapped_column(ForeignKey("warehouses.id"))  # satış: araç deposu
    active: Mapped[bool] = mapped_column(default=True)
    must_change_password: Mapped[bool] = mapped_column(default=False)  # yönetici şifreyi sıfırladıysa
    email: Mapped[str | None] = mapped_column(String(120))  # alarm ve rapor e-postaları için


class AuthSession(Base):
    """Oturum belirteçleri; belirtecin kendisi değil SHA-256 özeti saklanır."""

    __tablename__ = "sessions"

    token_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP, default=utcnow)
    expires_at: Mapped[datetime] = mapped_column(TIMESTAMP)


class Product(IdMixin, SyncMixin, Base):
    __tablename__ = "products"
    __table_args__ = (
        CheckConstraint("base_unit <> 'ADET' OR unit_weight_kg IS NOT NULL", name="adet_needs_weight"),
        CheckConstraint("sale_price IS NULL OR sale_price >= 0", name="sale_price_nonnegative"),
    )

    code: Mapped[str] = mapped_column(String(30), unique=True)
    name: Mapped[str] = mapped_column(String(100))
    kind: Mapped[ProductKind] = mapped_column(db_enum(ProductKind))
    base_unit: Mapped[BaseUnit] = mapped_column(db_enum(BaseUnit))
    unit_weight_kg: Mapped[Decimal | None] = mapped_column(QTY)  # ADET ürünlerde 1 adedin kg'ı
    lot_prefix: Mapped[str | None] = mapped_column(String(10))
    default_purchase_price: Mapped[Decimal | None] = mapped_column(PRICE)  # FR-101; gerçek fiyat lotta
    sale_price: Mapped[Decimal | None] = mapped_column(MONEY)  # VKP, net €/temel birim
    shelf_life_days: Mapped[int | None] = mapped_column(Integer)
    min_stock: Mapped[Decimal | None] = mapped_column(QTY)  # bunun altına düşünce kritik stok uyarısı
    active: Mapped[bool] = mapped_column(default=True)


class Partner(IdMixin, SyncMixin, Base):
    """Tedarikçi, müşteri ve dış üretici tek tabloda, rol bayraklarıyla."""

    __tablename__ = "partners"

    code: Mapped[str] = mapped_column(String(30), unique=True)
    name: Mapped[str] = mapped_column(String(150))
    is_supplier: Mapped[bool] = mapped_column(default=False)
    is_customer: Mapped[bool] = mapped_column(default=False)
    is_subcontractor: Mapped[bool] = mapped_column(default=False)
    parent_id: Mapped[int | None] = mapped_column(ForeignKey("partners.id"))  # şube → ana firma
    contact_person: Mapped[str | None] = mapped_column(String(100))
    phone: Mapped[str | None] = mapped_column(String(30))
    email: Mapped[str | None] = mapped_column(String(120))
    address: Mapped[str | None] = mapped_column(String(255))


class Warehouse(IdMixin, Base):
    __tablename__ = "warehouses"
    __table_args__ = (
        CheckConstraint(
            "kind <> 'DIS_URETICI' OR partner_id IS NOT NULL", name="subcontractor_needs_partner"
        ),
    )

    code: Mapped[str] = mapped_column(String(30), unique=True)
    name: Mapped[str] = mapped_column(String(100))
    kind: Mapped[WarehouseKind] = mapped_column(db_enum(WarehouseKind))
    partner_id: Mapped[int | None] = mapped_column(ForeignKey("partners.id"))


class NumberSequence(IdMixin, Base):
    """Belge numaraları (URT, PRC, SAT …); satır kilidiyle artırılır."""

    __tablename__ = "number_sequences"
    __table_args__ = (UniqueConstraint("prefix", "year"),)

    prefix: Mapped[str] = mapped_column(String(10))
    year: Mapped[int] = mapped_column(Integer)
    last_no: Mapped[int] = mapped_column(Integer, default=0)
