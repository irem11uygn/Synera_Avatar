"""Parçalama reçeteleri ve işlemleri (data_model.md §2.5)."""

from datetime import datetime
from decimal import Decimal

from sqlalchemy import CheckConstraint, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base
from app.models.enums import AllocationMethod, CuttingStatus, RecipeLineType, Species
from app.models.types import MONEY, PRICE, QTY, RATIO, TIMESTAMP, AuditMixin, IdMixin, db_enum, utcnow


class CuttingRecipe(IdMixin, Base):
    __tablename__ = "cutting_recipes"
    __table_args__ = (CheckConstraint("tolerance_kg >= 0", name="tolerance_nonnegative"),)

    code: Mapped[str] = mapped_column(String(30), unique=True)
    name: Mapped[str] = mapped_column(String(100))
    input_product_id: Mapped[int] = mapped_column(ForeignKey("products.id"))
    species: Mapped[Species] = mapped_column(db_enum(Species))
    default_method: Mapped[AllocationMethod] = mapped_column(db_enum(AllocationMethod))
    tolerance_kg: Mapped[Decimal] = mapped_column(QTY)


class CuttingRecipeLine(IdMixin, Base):
    __tablename__ = "cutting_recipe_lines"
    __table_args__ = (
        UniqueConstraint("recipe_id", "sort_order"),
        CheckConstraint("line_type = 'FIRE' OR product_id IS NOT NULL", name="product_required"),
        CheckConstraint(
            "line_type <> 'FIRE' OR (product_id IS NULL AND bears_cost = 0)",
            name="fire_has_no_product_or_cost",
        ),
        CheckConstraint("standard_ratio >= 0 AND standard_ratio <= 1", name="ratio_in_range"),
    )

    recipe_id: Mapped[int] = mapped_column(ForeignKey("cutting_recipes.id"))
    line_type: Mapped[RecipeLineType] = mapped_column(db_enum(RecipeLineType))
    product_id: Mapped[int | None] = mapped_column(ForeignKey("products.id"))
    standard_ratio: Mapped[Decimal] = mapped_column(RATIO)  # Model B'nin referans yöntemi
    value_per_kg: Mapped[Decimal | None] = mapped_column(PRICE)  # değer ağırlıklı dağıtım katsayısı
    bears_cost: Mapped[bool] = mapped_column(default=True)
    sort_order: Mapped[int] = mapped_column(Integer)  # dağıtımda eşitlik bozucu


class Cutting(IdMixin, AuditMixin, Base):
    __tablename__ = "cuttings"
    __table_args__ = (CheckConstraint("input_qty > 0", name="input_qty_positive"),)

    cutting_no: Mapped[str] = mapped_column(String(30), unique=True)
    recipe_id: Mapped[int] = mapped_column(ForeignKey("cutting_recipes.id"))
    input_lot_id: Mapped[int] = mapped_column(ForeignKey("lots.id"))
    input_qty: Mapped[Decimal] = mapped_column(QTY)
    species: Mapped[Species] = mapped_column(db_enum(Species))
    method: Mapped[AllocationMethod] = mapped_column(db_enum(AllocationMethod))
    status: Mapped[CuttingStatus] = mapped_column(db_enum(CuttingStatus), default=CuttingStatus.TASLAK)
    total_cost: Mapped[Decimal | None] = mapped_column(MONEY)
    cut_at: Mapped[datetime] = mapped_column(TIMESTAMP, default=utcnow)
    approved_at: Mapped[datetime | None] = mapped_column(TIMESTAMP)


class CuttingOutput(IdMixin, Base):
    __tablename__ = "cutting_outputs"
    __table_args__ = (
        CheckConstraint("actual_qty IS NULL OR actual_qty >= 0", name="actual_qty_nonnegative"),
    )

    cutting_id: Mapped[int] = mapped_column(ForeignKey("cuttings.id"))
    recipe_line_id: Mapped[int] = mapped_column(ForeignKey("cutting_recipe_lines.id"))
    line_type: Mapped[RecipeLineType] = mapped_column(db_enum(RecipeLineType))
    product_id: Mapped[int | None] = mapped_column(ForeignKey("products.id"))
    actual_qty: Mapped[Decimal | None] = mapped_column(QTY)
    predicted_qty: Mapped[Decimal | None] = mapped_column(QTY)  # Model B tahmini
    allocated_cost: Mapped[Decimal | None] = mapped_column(MONEY)
    output_lot_id: Mapped[int | None] = mapped_column(ForeignKey("lots.id"), unique=True)
