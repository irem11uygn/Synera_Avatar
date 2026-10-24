"""Android senkronizasyonu (api.md §4.4). Ondalıklar JSON'da metin olarak döner (ADR-006)."""

from datetime import date
from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, ConfigDict

from app.api.deps import Db, require_role
from app.models import User
from app.models.enums import BaseUnit, LotStatus, UserRole
from app.services.sync import pull_changes

router = APIRouter(prefix="/sync", tags=["senkronizasyon"])


class _FromModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class ProductOut(_FromModel):
    id: int
    code: str
    name: str
    base_unit: BaseUnit
    unit_weight_kg: Decimal | None
    sale_price: Decimal | None
    active: bool


class CustomerOut(_FromModel):
    id: int
    code: str
    name: str
    contact_person: str | None
    phone: str | None
    email: str | None
    address: str | None


class LotOut(_FromModel):
    id: int
    lot_no: str
    product_id: int
    expiry_date: date | None
    status: LotStatus


class StockOut(_FromModel):
    lot_id: int
    qty: Decimal


class PullResponse(BaseModel):
    next_since: int
    products: list[ProductOut]
    customers: list[CustomerOut]
    lots: list[LotOut]
    stock: list[StockOut]


@router.get("/pull", response_model=PullResponse)
def pull(
    db: Db,
    user: Annotated[User, Depends(require_role(UserRole.SATIS))],
    since: Annotated[int, Query(ge=0, description="Cihazın son aldığı değişiklik numarası")] = 0,
) -> PullResponse:
    result = pull_changes(db, user, since)
    return PullResponse(
        next_since=result.next_since,
        products=[ProductOut.model_validate(p) for p in result.products],
        customers=[CustomerOut.model_validate(c) for c in result.customers],
        lots=[LotOut.model_validate(lot) for lot in result.lots],
        stock=[StockOut.model_validate(s) for s in result.stock],
    )
