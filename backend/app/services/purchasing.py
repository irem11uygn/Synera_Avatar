"""Hammadde alışı: her satır yeni lot + alış girişi (FR-102, FR-203, FR-207)."""

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy.orm import Session

from app.domain.costing import line_amount
from app.errors import AmountMismatchNoteRequired, InvalidInput, NotFound
from app.models import Partner, Product, Purchase, PurchaseCost, PurchaseLine
from app.models.enums import DocType, LotOrigin, MovementType, PurchaseCostKind
from app.services.ledger import create_lot


@dataclass(frozen=True)
class ExtraCost:
    kind: PurchaseCostKind
    amount: Decimal
    note: str | None = None


@dataclass(frozen=True)
class PurchaseLineInput:
    product_id: int
    lot_no: str
    qty: Decimal
    unit_price: Decimal
    invoice_amount: Decimal | None = None  # boşsa miktar × birim fiyat
    discrepancy_note: str | None = None
    expiry_date: date | None = None  # boşsa alış tarihi + ürünün raf ömrü
    extra_costs: Sequence[ExtraCost] = ()


def create_purchase(
    session: Session,
    *,
    supplier_id: int,
    doc_no: str,
    doc_date: date,
    warehouse_id: int,
    lines: Sequence[PurchaseLineInput],
    note: str | None = None,
    user_id: int | None = None,
) -> Purchase:
    """Alış belgesini kaydeder. Lot değeri = fatura tutarı + ek maliyet kalemleri."""
    supplier = session.get(Partner, supplier_id)
    if supplier is None or not supplier.is_supplier:
        raise InvalidInput(
            "Alış yalnız tedarikçi olarak tanımlı bir cariden yapılabilir.", supplier_id=supplier_id
        )
    if not lines:
        raise InvalidInput("Alış belgesinde en az bir satır olmalı.")

    purchase = Purchase(
        doc_no=doc_no, supplier_id=supplier_id, doc_date=doc_date, note=note, created_by=user_id
    )
    session.add(purchase)
    session.flush()
    for line in lines:
        _add_line(session, purchase, line, warehouse_id, user_id)
    return purchase


def _add_line(
    session: Session, purchase: Purchase, line: PurchaseLineInput, warehouse_id: int, user_id: int | None
) -> None:
    product = session.get(Product, line.product_id)
    if product is None:
        raise NotFound("Ürün bulunamadı.", product_id=line.product_id)
    if line.qty <= 0 or line.unit_price < 0 or any(cost.amount < 0 for cost in line.extra_costs):
        raise InvalidInput("Miktar pozitif; fiyat ve ek maliyetler eksi olmamalı.", lot_no=line.lot_no)

    computed = line_amount(line.qty, line.unit_price)
    invoice = computed if line.invoice_amount is None else line.invoice_amount
    note = (line.discrepancy_note or "").strip() or None
    if invoice != computed and note is None:
        raise AmountMismatchNoteRequired(
            f"{line.lot_no}: fatura tutarı ({invoice} €) miktar × birim fiyattan ({computed} €) farklı; "
            "farkın nedenini açıklayın.",
            lot_no=line.lot_no,
            computed_amount=computed,
            invoice_amount=invoice,
        )

    expiry = line.expiry_date
    if expiry is None and product.shelf_life_days:
        expiry = purchase.doc_date + timedelta(days=product.shelf_life_days)
    lot = create_lot(
        session,
        lot_no=line.lot_no,
        product_id=product.id,
        origin=LotOrigin.ALIS,
        qty=line.qty,
        value=invoice + sum((cost.amount for cost in line.extra_costs), Decimal(0)),
        warehouse_id=warehouse_id,
        movement_type=MovementType.ALIS_GIRIS,
        doc_type=DocType.ALIS,
        doc_id=purchase.id,
        supplier_id=purchase.supplier_id,
        expiry_date=expiry,
        user_id=user_id,
    )
    purchase_line = PurchaseLine(
        purchase_id=purchase.id,
        product_id=product.id,
        lot_id=lot.id,
        qty=line.qty,
        unit_price=line.unit_price,
        computed_amount=computed,
        invoice_amount=invoice,
        discrepancy_note=note,
        expiry_date=expiry,
    )
    session.add(purchase_line)
    session.flush()
    session.add_all(
        PurchaseCost(purchase_line_id=purchase_line.id, kind=cost.kind, amount=cost.amount, note=cost.note)
        for cost in line.extra_costs
    )
    session.flush()
