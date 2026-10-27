"""İleri ve geri izleme (FR-304, FR-305, FR-308; api.md §4.3)."""

from datetime import date
from decimal import Decimal

from fastapi import APIRouter
from pydantic import BaseModel, ConfigDict

from app.api.deps import AdminUser, Db
from app.api.fields import UtcDateTime
from app.models.enums import BaseUnit, LinkProcess, LotOrigin, LotStatus, SaleChannel, WarehouseKind
from app.services.trace import OnwardStatus, trace_backward, trace_forward

router = APIRouter(prefix="/trace", tags=["izleme"])


class _Out(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class ContactOut(_Out):
    person: str | None
    phone: str | None
    email: str | None
    address: str | None


class TracedLotOut(_Out):
    lot_no: str
    product_code: str
    product_name: str
    base_unit: BaseUnit
    origin: LotOrigin
    status: LotStatus
    depth: int
    initial_qty: Decimal
    remaining_qty: Decimal
    supplier_name: str | None
    produced_at: date | None
    expiry_date: date | None


class TraceLinkOut(_Out):
    parent_lot_no: str
    child_lot_no: str
    qty: Decimal
    process: LinkProcess
    doc_no: str | None


class StockItemOut(_Out):
    lot_no: str
    product_name: str
    base_unit: BaseUnit
    warehouse_code: str
    warehouse_name: str
    warehouse_kind: WarehouseKind
    qty: Decimal


class SaleRefOut(_Out):
    sale_id: int
    sale_no: str
    sale_line_id: int
    channel: SaleChannel
    sold_at: UtcDateTime
    qty: Decimal
    returned_qty: Decimal
    recall_violation: bool


class OnwardItemOut(_Out):
    recipient: str
    qty: Decimal
    delivered_at: date | None
    source_note: str | None
    contact: ContactOut


class RecipientOut(_Out):
    customer_id: int
    customer: str
    contact: ContactOut
    lot_no: str
    product_name: str
    base_unit: BaseUnit
    sold_qty: Decimal
    returned_qty: Decimal
    qty: Decimal
    sales: list[SaleRefOut]
    onward_status: OnwardStatus
    onward_items: list[OnwardItemOut]
    onward_unknown_qty: Decimal
    recall_violation: bool


class SupplierRefOut(_Out):
    lot_no: str
    supplier: str
    contact: ContactOut
    purchase_doc_no: str | None
    purchase_date: date | None
    qty: Decimal


class ProcessRefOut(_Out):
    process: LinkProcess
    doc_no: str | None
    input_lots: list[str]
    output_lots: list[str]


class TraceOut(_Out):
    source: TracedLotOut
    lots: list[TracedLotOut]
    links: list[TraceLinkOut]
    stock: list[StockItemOut]
    recipients: list[RecipientOut]
    suppliers: list[SupplierRefOut]
    processes: list[ProcessRefOut]


@router.get("/forward/{lot_no}", response_model=TraceOut)
def forward(lot_no: str, db: Db, _: AdminUser) -> TraceOut:
    """Türev lotlar, bizdeki stok, alıcılar (miktar, satış belgesi, iletişim, ikinci kademe)."""
    return TraceOut.model_validate(trace_forward(db, lot_no))


@router.get("/backward/{lot_no}", response_model=TraceOut)
def backward(lot_no: str, db: Db, _: AdminUser) -> TraceOut:
    """Lotu oluşturan bütün lotlar, tedarikçiler ve alış belgeleri, üretim emirleri ve parçalamalar."""
    return TraceOut.model_validate(trace_backward(db, lot_no))
