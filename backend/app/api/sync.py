"""Android senkronizasyonu (api.md §4.4). Ondalıklar JSON'da metin olarak döner (ADR-006)."""

from datetime import date, datetime
from decimal import Decimal
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, ConfigDict, Field

from app.api.deps import Db, require_role
from app.models import User
from app.models.enums import BaseUnit, LotStatus, PaymentMethod, UserRole
from app.services import sales
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
    dataset_id: str
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
        dataset_id=result.dataset_id,
        next_since=result.next_since,
        products=[ProductOut.model_validate(p) for p in result.products],
        customers=[CustomerOut.model_validate(c) for c in result.customers],
        lots=[LotOut.model_validate(lot) for lot in result.lots],
        stock=[StockOut.model_validate(s) for s in result.stock],
    )


class PushLineIn(BaseModel):
    lot_no: str = Field(min_length=1, max_length=40)
    qty: Decimal = Field(gt=0, max_digits=12, decimal_places=3)
    unit_price: Decimal = Field(ge=0, max_digits=14, decimal_places=4)


class PushSaleIn(BaseModel):
    client_uuid: UUID  # cihazda üretilir; tekrar güvenlik anahtarı
    customer_id: int
    warehouse_id: int
    sold_at: datetime
    lines: list[PushLineIn] = Field(min_length=1, max_length=50)
    payment_method: PaymentMethod | None = None  # eski uygulama sürümleri göndermez


class PushIn(BaseModel):
    device_id: str | None = Field(default=None, max_length=64)
    sales: list[PushSaleIn] = Field(max_length=200)


class PushErrorOut(BaseModel):
    code: str
    message: str


class PushResultOut(BaseModel):
    client_uuid: str
    status: sales.PushStatus
    sale_no: str | None
    warnings: list[str]
    error: PushErrorOut | None


class PushResponse(BaseModel):
    results: list[PushResultOut]


@router.post("/push", response_model=PushResponse)
def push(body: PushIn, db: Db, user: Annotated[User, Depends(require_role(UserRole.SATIS))]) -> PushResponse:
    """Cihazdaki bekleyen satışları kaydeder; her satışın sonucu ayrı döner (api.md §4.4)."""
    results = sales.push_sales(
        db,
        user,
        body.device_id,
        [
            sales.SaleInput(
                client_uuid=str(sale.client_uuid),
                customer_id=sale.customer_id,
                warehouse_id=sale.warehouse_id,
                sold_at=sale.sold_at,
                lines=[sales.SaleLineInput(line.lot_no, line.qty, line.unit_price) for line in sale.lines],
                payment_method=sale.payment_method,
            )
            for sale in body.sales
        ],
    )
    return PushResponse(
        results=[
            PushResultOut(
                client_uuid=r.client_uuid,
                status=r.status,
                sale_no=r.sale_no,
                warnings=r.warnings,
                error=PushErrorOut(code=r.error_code, message=r.error_message or "")
                if r.error_code
                else None,
            )
            for r in results
        ]
    )
