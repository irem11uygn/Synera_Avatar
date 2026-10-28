"""Hammadde alışı (FR-102, FR-203, FR-207). Her satır yeni bir lot açar."""

from datetime import date
from decimal import Decimal

from fastapi import APIRouter
from pydantic import BaseModel, Field
from sqlalchemy import select

from app.api.deps import Db, StockUser, WebUser
from app.models import Lot, Partner, Product, Purchase, PurchaseCost, PurchaseLine
from app.models.enums import PurchaseCostKind
from app.services import alarms, audit
from app.services.invoice_text import parse_invoice_text
from app.services.lookups import get_or_404, main_warehouse
from app.services.purchasing import ExtraCost, PurchaseLineInput, create_purchase

router = APIRouter(prefix="/purchases", tags=["alış"])


class ExtraCostIn(BaseModel):
    kind: PurchaseCostKind
    amount: Decimal = Field(ge=0, max_digits=14, decimal_places=2)
    note: str | None = Field(default=None, max_length=255)


class PurchaseLineIn(BaseModel):
    product_id: int
    lot_no: str = Field(min_length=1, max_length=40)
    qty: Decimal = Field(gt=0, max_digits=12, decimal_places=3)
    unit_price: Decimal = Field(ge=0, max_digits=14, decimal_places=4)
    invoice_amount: Decimal | None = Field(default=None, ge=0, max_digits=14, decimal_places=2)
    discrepancy_note: str | None = Field(default=None, max_length=500)
    expiry_date: date | None = None
    extra_costs: list[ExtraCostIn] = []


class PurchaseIn(BaseModel):
    supplier_id: int
    doc_no: str = Field(min_length=1, max_length=50)
    doc_date: date
    warehouse_id: int | None = None  # boşsa ana depo
    note: str | None = Field(default=None, max_length=255)
    lines: list[PurchaseLineIn] = Field(min_length=1)


class ExtraCostOut(BaseModel):
    kind: PurchaseCostKind
    amount: Decimal
    note: str | None


class PurchaseLineOut(BaseModel):
    lot_no: str
    product_code: str
    product_name: str
    qty: Decimal
    unit_price: Decimal
    computed_amount: Decimal
    invoice_amount: Decimal
    discrepancy_note: str | None
    extra_costs: list[ExtraCostOut]
    lot_value: Decimal
    expiry_date: date | None


class PurchaseOut(BaseModel):
    id: int
    doc_no: str
    doc_date: date
    supplier_id: int
    supplier_name: str
    note: str | None
    lines: list[PurchaseLineOut]
    total_value: Decimal


def _purchase_out(db: Db, purchase: Purchase) -> PurchaseOut:
    supplier = db.get(Partner, purchase.supplier_id)
    assert supplier is not None
    lines = []
    for line in db.scalars(
        select(PurchaseLine).where(PurchaseLine.purchase_id == purchase.id).order_by(PurchaseLine.id)
    ):
        product, lot = db.get(Product, line.product_id), db.get(Lot, line.lot_id)
        assert product is not None and lot is not None
        costs = db.scalars(select(PurchaseCost).where(PurchaseCost.purchase_line_id == line.id)).all()
        lines.append(
            PurchaseLineOut(
                lot_no=lot.lot_no,
                product_code=product.code,
                product_name=product.name,
                qty=line.qty,
                unit_price=line.unit_price,
                computed_amount=line.computed_amount,
                invoice_amount=line.invoice_amount,
                discrepancy_note=line.discrepancy_note,
                extra_costs=[ExtraCostOut(kind=c.kind, amount=c.amount, note=c.note) for c in costs],
                lot_value=lot.initial_value,
                expiry_date=line.expiry_date,
            )
        )
    return PurchaseOut(
        id=purchase.id,
        doc_no=purchase.doc_no,
        doc_date=purchase.doc_date,
        supplier_id=supplier.id,
        supplier_name=supplier.name,
        note=purchase.note,
        lines=lines,
        total_value=sum((line.lot_value for line in lines), Decimal("0.00")),
    )


@router.post("", response_model=PurchaseOut, status_code=201)
def create(body: PurchaseIn, db: Db, user: StockUser) -> PurchaseOut:
    purchase = create_purchase(
        db,
        supplier_id=body.supplier_id,
        doc_no=body.doc_no,
        doc_date=body.doc_date,
        warehouse_id=body.warehouse_id or main_warehouse(db).id,
        note=body.note,
        user_id=user.id,
        lines=[
            PurchaseLineInput(
                product_id=line.product_id,
                lot_no=line.lot_no,
                qty=line.qty,
                unit_price=line.unit_price,
                invoice_amount=line.invoice_amount,
                discrepancy_note=line.discrepancy_note,
                expiry_date=line.expiry_date,
                extra_costs=[ExtraCost(c.kind, c.amount, c.note) for c in line.extra_costs],
            )
            for line in body.lines
        ],
    )
    out = _purchase_out(db, purchase)
    audit.log(
        db,
        "MAL_KABUL",
        f"Mal kabul {purchase.doc_no} ({out.supplier_name}): {len(out.lines)} satır, "
        f"lotlar {', '.join(line.lot_no for line in out.lines)}",
        user=user,
        ref_type="PURCHASE",
        ref_id=purchase.id,
    )
    alarms.run_rules(db, user)  # fiyat artışı hemen görünsün
    return out


@router.get("", response_model=list[PurchaseOut])
def list_purchases(db: Db, _: WebUser) -> list[PurchaseOut]:
    purchases = db.scalars(select(Purchase).order_by(Purchase.doc_date.desc(), Purchase.id.desc()))
    return [_purchase_out(db, purchase) for purchase in purchases]


@router.get("/{purchase_id}", response_model=PurchaseOut)
def get_purchase(purchase_id: int, db: Db, _: WebUser) -> PurchaseOut:
    return _purchase_out(db, get_or_404(db, Purchase, purchase_id, "Alış belgesi"))


class ParseTextIn(BaseModel):
    text: str = Field(min_length=1, max_length=20000)


class LineSuggestionOut(BaseModel):
    source: str
    product_id: int | None
    product_code: str | None
    product_name: str | None
    match: str
    qty: Decimal | None
    unit: str | None
    unit_price: Decimal | None
    invoice_amount: Decimal | None
    lot_no: str | None
    expiry_date: date | None
    warnings: list[str]


class InvoiceSuggestionOut(BaseModel):
    supplier_id: int | None
    supplier_name: str | None
    doc_no: str | None
    doc_date: date | None
    lines: list[LineSuggestionOut]
    warnings: list[str]


@router.post("/parse-text", response_model=InvoiceSuggestionOut)
def parse_text(body: ParseTextIn, db: Db, _: StockUser) -> InvoiceSuggestionOut:
    """Fatura/irsaliye metninden mal kabul önerisi. Hiçbir şey kaydetmez; kullanıcı kontrol edip kaydeder."""
    result = parse_invoice_text(db, body.text)
    return InvoiceSuggestionOut(
        supplier_id=result.supplier_id,
        supplier_name=result.supplier_name,
        doc_no=result.doc_no,
        doc_date=result.doc_date,
        lines=[LineSuggestionOut(**vars(line)) for line in result.lines],
        warnings=result.warnings,
    )
