"""Ana veriler: ürün, cari, depo (api.md §2 — Ana veriler)."""

from decimal import Decimal
from typing import Annotated, Literal

from fastapi import APIRouter, Query
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select

from app.api.deps import AdminUser, Db, PartnerUser, WebUser
from app.models import Partner, Product, Warehouse
from app.models.enums import BaseUnit, ProductKind, WarehouseKind
from app.services.lookups import get_or_404
from app.services.master import save_partner, save_product

router = APIRouter(tags=["ana veriler"])


class ProductIn(BaseModel):
    code: str = Field(min_length=1, max_length=30)
    name: str = Field(min_length=1, max_length=100)
    kind: ProductKind
    base_unit: BaseUnit
    unit_weight_kg: Decimal | None = Field(default=None, gt=0, max_digits=12, decimal_places=3)
    lot_prefix: str | None = Field(default=None, max_length=10)
    default_purchase_price: Decimal | None = Field(default=None, ge=0, max_digits=14, decimal_places=4)
    sale_price: Decimal | None = Field(default=None, ge=0, max_digits=14, decimal_places=2)
    shelf_life_days: int | None = Field(default=None, ge=0)
    min_stock: Decimal | None = Field(default=None, ge=0, max_digits=12, decimal_places=3)  # kritik stok
    active: bool = True


class ProductOut(ProductIn):
    model_config = ConfigDict(from_attributes=True)
    id: int


class PartnerIn(BaseModel):
    code: str = Field(min_length=1, max_length=30)
    name: str = Field(min_length=1, max_length=150)
    is_supplier: bool = False
    is_customer: bool = False
    is_subcontractor: bool = False
    parent_id: int | None = None
    contact_person: str | None = Field(default=None, max_length=100)
    phone: str | None = Field(default=None, max_length=30)
    email: str | None = Field(default=None, max_length=120)
    address: str | None = Field(default=None, max_length=255)


class PartnerOut(PartnerIn):
    model_config = ConfigDict(from_attributes=True)
    id: int


class WarehouseOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    code: str
    name: str
    kind: WarehouseKind
    partner_id: int | None


@router.get("/products", response_model=list[ProductOut])
def list_products(db: Db, _: WebUser, kind: ProductKind | None = None) -> list[Product]:
    query = select(Product).order_by(Product.code)
    if kind is not None:
        query = query.where(Product.kind == kind)
    return list(db.scalars(query))


@router.post("/products", response_model=ProductOut, status_code=201)
def create_product(body: ProductIn, db: Db, _: AdminUser) -> Product:
    return save_product(db, None, body.model_dump())


@router.put("/products/{product_id}", response_model=ProductOut)
def update_product(product_id: int, body: ProductIn, db: Db, _: AdminUser) -> Product:
    return save_product(db, get_or_404(db, Product, product_id, "Ürün"), body.model_dump())


@router.get("/partners", response_model=list[PartnerOut])
def list_partners(
    db: Db,
    _: WebUser,
    role: Annotated[Literal["supplier", "customer", "subcontractor"] | None, Query()] = None,
) -> list[Partner]:
    query = select(Partner).order_by(Partner.code)
    if role is not None:
        query = query.where(getattr(Partner, f"is_{role}"))
    return list(db.scalars(query))


@router.post("/partners", response_model=PartnerOut, status_code=201)
def create_partner(body: PartnerIn, db: Db, _: PartnerUser) -> Partner:
    return save_partner(db, None, body.model_dump())


@router.put("/partners/{partner_id}", response_model=PartnerOut)
def update_partner(partner_id: int, body: PartnerIn, db: Db, _: PartnerUser) -> Partner:
    return save_partner(db, get_or_404(db, Partner, partner_id, "Cari"), body.model_dump())


@router.get("/warehouses", response_model=list[WarehouseOut])
def list_warehouses(db: Db, _: WebUser) -> list[Warehouse]:
    return list(db.scalars(select(Warehouse).order_by(Warehouse.id)))
