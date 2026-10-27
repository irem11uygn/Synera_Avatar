"""İleri ve geri izleme (FR-304, FR-305, FR-308).

Yalnız kesin kayıtlara dayanır: lot bağları, stok bakiyeleri, satış satırları, iadeler ve müşterinin
bildirdiği ikinci kademe teslimatlar. Tahmin içermez (CON-003). İkinci kademe dağıtım kayıtlı değilse
müşteri "bilinen son alıcı" olarak kalır ve sonrası "bilinmiyor" diye işaretlenir.
"""

from collections import defaultdict
from collections.abc import Collection
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import (
    CustomerReturn,
    Lot,
    LotLink,
    OnwardDelivery,
    Partner,
    Product,
    Purchase,
    PurchaseLine,
    Sale,
    SaleLine,
    StockBalance,
    StockMovement,
    Warehouse,
)
from app.models.enums import (
    BaseUnit,
    DocType,
    LinkProcess,
    LotOrigin,
    LotStatus,
    SaleChannel,
    WarehouseKind,
)
from app.services.lookups import document_numbers, lot_by_no
from app.services.lot_graph import ancestors, descendants

_PROCESS_DOC = {
    LinkProcess.URETIM: DocType.URETIM,
    LinkProcess.PARCALAMA: DocType.PARCALAMA,
    LinkProcess.YENIDEN_ISLEME: DocType.URETIM,
}


class OnwardStatus(StrEnum):
    KAYITLI = "KAYITLI"  # müşterinin bütün miktarının nereye gittiği kayıtlı (kesin)
    KISMEN = "KISMEN"  # bir kısmı kayıtlı, kalanı bilinmiyor
    BILINMIYOR = "BILINMIYOR"  # kayıt yok: müşteri bilinen son alıcı


@dataclass(frozen=True)
class Contact:
    person: str | None
    phone: str | None
    email: str | None
    address: str | None


@dataclass(frozen=True)
class TracedLot:
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


@dataclass(frozen=True)
class TraceLink:
    parent_lot_no: str
    child_lot_no: str
    qty: Decimal
    process: LinkProcess
    doc_no: str | None


@dataclass(frozen=True)
class StockItem:
    lot_no: str
    product_name: str
    base_unit: BaseUnit
    warehouse_code: str
    warehouse_name: str
    warehouse_kind: WarehouseKind
    qty: Decimal


@dataclass(frozen=True)
class SaleRef:
    sale_id: int
    sale_no: str
    sale_line_id: int
    channel: SaleChannel
    sold_at: datetime
    qty: Decimal
    returned_qty: Decimal
    recall_violation: bool


@dataclass(frozen=True)
class OnwardItem:
    recipient: str
    qty: Decimal
    delivered_at: date | None
    source_note: str | None
    contact: Contact


@dataclass(frozen=True)
class Recipient:
    customer_id: int
    customer: str
    contact: Contact
    lot_no: str
    product_name: str
    base_unit: BaseUnit
    sold_qty: Decimal
    returned_qty: Decimal
    qty: Decimal  # müşteride kalan = satılan − iade
    sales: list[SaleRef]
    onward_status: OnwardStatus
    onward_items: list[OnwardItem]
    onward_unknown_qty: Decimal  # müşteriden sonrası bilinmeyen miktar
    recall_violation: bool


@dataclass(frozen=True)
class SupplierRef:
    lot_no: str
    supplier: str
    contact: Contact
    purchase_doc_no: str | None
    purchase_date: date | None
    qty: Decimal


@dataclass(frozen=True)
class ProcessRef:
    process: LinkProcess
    doc_no: str | None
    input_lots: list[str]
    output_lots: list[str]


@dataclass
class Trace:
    source: TracedLot
    lots: list[TracedLot]
    links: list[TraceLink]
    stock: list[StockItem] = field(default_factory=list)
    recipients: list[Recipient] = field(default_factory=list)
    suppliers: list[SupplierRef] = field(default_factory=list)
    processes: list[ProcessRef] = field(default_factory=list)


def trace_forward(session: Session, lot_no: str) -> Trace:
    """Lot ve ondan türeyen bütün lotlar; bizdeki stok, satışlar, alıcılar ve ikinci kademe."""
    source = lot_by_no(session, lot_no)
    depths = descendants(session, source.id)
    lots = traced_lots(session, depths)
    return Trace(
        source=lots[0],
        lots=lots,
        links=_links(session, depths.keys()),
        stock=stock_of(session, depths.keys()),
        recipients=recipients_of(session, depths.keys()),
    )


def trace_backward(session: Session, lot_no: str) -> Trace:
    """Lotu oluşturan bütün lotlar; tedarikçiler, alış belgeleri, üretim emirleri ve parçalamalar."""
    target = lot_by_no(session, lot_no)
    depths = ancestors(session, target.id)
    lots = traced_lots(session, depths)
    links = _links(session, depths.keys())
    return Trace(
        source=lots[0],
        lots=lots,
        links=links,
        suppliers=_suppliers(session, depths.keys()),
        processes=_processes(links),
    )


def traced_lots(session: Session, depths: dict[int, int]) -> list[TracedLot]:
    """Lotlar derinlik, sonra lot kimliği sırasıyla; ilk eleman başlangıç lotu (derinlik 0)."""
    rows = session.execute(
        select(Lot, Product, Partner.name)
        .join(Product, Product.id == Lot.product_id)
        .outerjoin(Partner, Partner.id == Lot.supplier_id)
        .where(Lot.id.in_(depths))
    ).all()
    result = [
        TracedLot(
            lot_no=lot.lot_no,
            product_code=product.code,
            product_name=product.name,
            base_unit=product.base_unit,
            origin=lot.origin,
            status=lot.status,
            depth=depths[lot.id],
            initial_qty=lot.initial_qty,
            remaining_qty=lot.remaining_qty,
            supplier_name=supplier,
            produced_at=lot.produced_at,
            expiry_date=lot.expiry_date,
        )
        for lot, product, supplier in sorted(rows, key=lambda r: (depths[r[0].id], r[0].id))
    ]
    return result


def _links(session: Session, lot_ids: Collection[int]) -> list[TraceLink]:
    """İzlenen lotlar arasındaki bağlar (ör. ET-2026-001 → SUC-2026-045, 100 kg, URT-2026-045)."""
    links = session.scalars(
        select(LotLink)
        .where(LotLink.parent_lot_id.in_(lot_ids), LotLink.child_lot_id.in_(lot_ids))
        .order_by(LotLink.id)
    ).all()
    numbers = _lot_numbers(session, lot_ids)
    docs = document_numbers(session, ((_PROCESS_DOC[link.process], link.process_id) for link in links))
    return [
        TraceLink(
            parent_lot_no=numbers[link.parent_lot_id],
            child_lot_no=numbers[link.child_lot_id],
            qty=link.qty,
            process=link.process,
            doc_no=docs.get((_PROCESS_DOC[link.process], link.process_id)),
        )
        for link in links
    ]


def stock_of(session: Session, lot_ids: Collection[int]) -> list[StockItem]:
    """Lotların bizdeki (ana depo, araç, dış üretici) bakiyeleri."""
    rows = session.execute(
        select(Lot.lot_no, Product.name, Product.base_unit, Warehouse, StockBalance.qty)
        .join(StockBalance, StockBalance.lot_id == Lot.id)
        .join(Warehouse, Warehouse.id == StockBalance.warehouse_id)
        .join(Product, Product.id == Lot.product_id)
        .where(Lot.id.in_(lot_ids), StockBalance.qty > 0)
        .order_by(Lot.id, Warehouse.id)
    ).all()
    return [
        StockItem(
            lot_no=lot_no,
            product_name=name,
            base_unit=unit,
            warehouse_code=warehouse.code,
            warehouse_name=warehouse.name,
            warehouse_kind=warehouse.kind,
            qty=qty,
        )
        for lot_no, name, unit, warehouse, qty in rows
    ]


def recipients_of(session: Session, lot_ids: Collection[int]) -> list[Recipient]:
    """Lotlardan satış yapılan müşteriler; müşteri × lot başına bir satır."""
    rows = session.execute(
        select(SaleLine, Sale, Partner, Lot.lot_no, Product.name, Product.base_unit)
        .join(Sale, Sale.id == SaleLine.sale_id)
        .join(Partner, Partner.id == Sale.customer_id)
        .join(Lot, Lot.id == SaleLine.lot_id)
        .join(Product, Product.id == SaleLine.product_id)
        .where(SaleLine.lot_id.in_(lot_ids))
        .order_by(Partner.name, Lot.id, Sale.id, SaleLine.line_no)
    ).all()
    line_ids = [line.id for line, *_ in rows]
    returned = returned_qty_by_line(session, line_ids)
    onward = _onward_by_line(session, line_ids)

    groups: dict[tuple[int, str], list] = defaultdict(list)
    for row in rows:
        groups[(row[2].id, row[3])].append(row)
    recipients = []
    for group in groups.values():
        _, _, customer, lot_no, product_name, unit = group[0]
        sales = [
            SaleRef(
                sale_id=sale.id,
                sale_no=sale.sale_no,
                sale_line_id=line.id,
                channel=sale.channel,
                sold_at=sale.sold_at,
                qty=line.qty,
                returned_qty=returned.get(line.id, Decimal(0)),
                recall_violation=sale.recall_violation,
            )
            for line, sale, *_ in group
        ]
        sold = sum((s.qty for s in sales), Decimal(0))
        back = sum((s.returned_qty for s in sales), Decimal(0))
        items = [item for s in sales for item in onward.get(s.sale_line_id, [])]
        known = sum((item.qty for item in items), Decimal(0))
        held = sold - back
        unknown = max(held - known, Decimal(0))
        if not items:
            status = OnwardStatus.BILINMIYOR
        elif unknown > 0:
            status = OnwardStatus.KISMEN
        else:
            status = OnwardStatus.KAYITLI
        recipients.append(
            Recipient(
                customer_id=customer.id,
                customer=customer.name,
                contact=_contact(customer),
                lot_no=lot_no,
                product_name=product_name,
                base_unit=unit,
                sold_qty=sold,
                returned_qty=back,
                qty=held,
                sales=sales,
                onward_status=status,
                onward_items=items,
                onward_unknown_qty=unknown,
                recall_violation=any(s.recall_violation for s in sales),
            )
        )
    return recipients


def returned_qty_by_line(session: Session, line_ids: Collection[int]) -> dict[int, Decimal]:
    """Satış satırı başına iade miktarı; ters kayıtla geri alınmış iadeler sayılmaz."""
    if not line_ids:
        return {}
    reversed_ids = select(StockMovement.reversal_of_id).where(StockMovement.reversal_of_id.is_not(None))
    rows = session.execute(
        select(CustomerReturn.sale_line_id, CustomerReturn.qty).where(
            CustomerReturn.sale_line_id.in_(line_ids),
            CustomerReturn.stock_movement_id.not_in(reversed_ids),
        )
    ).all()
    totals: dict[int, Decimal] = defaultdict(Decimal)
    for line_id, qty in rows:
        totals[line_id] += qty
    return dict(totals)


def _onward_by_line(session: Session, line_ids: Collection[int]) -> dict[int, list[OnwardItem]]:
    if not line_ids:
        return {}
    rows = session.execute(
        select(OnwardDelivery, Partner)
        .join(Partner, Partner.id == OnwardDelivery.recipient_partner_id)
        .where(OnwardDelivery.sale_line_id.in_(line_ids))
        .order_by(OnwardDelivery.id)
    ).all()
    items: dict[int, list[OnwardItem]] = defaultdict(list)
    for delivery, partner in rows:
        items[delivery.sale_line_id].append(
            OnwardItem(
                recipient=partner.name,
                qty=delivery.qty,
                delivered_at=delivery.delivered_at,
                source_note=delivery.source_note,
                contact=_contact(partner),
            )
        )
    return items


def _suppliers(session: Session, lot_ids: Collection[int]) -> list[SupplierRef]:
    rows = session.execute(
        select(Lot, Partner, Purchase.doc_no, Purchase.doc_date, PurchaseLine.qty)
        .join(Partner, Partner.id == Lot.supplier_id)
        .outerjoin(PurchaseLine, PurchaseLine.lot_id == Lot.id)
        .outerjoin(Purchase, Purchase.id == PurchaseLine.purchase_id)
        .where(Lot.id.in_(lot_ids), Lot.origin == LotOrigin.ALIS)
        .order_by(Lot.id)
    ).all()
    return [
        SupplierRef(
            lot_no=lot.lot_no,
            supplier=partner.name,
            contact=_contact(partner),
            purchase_doc_no=doc_no,
            purchase_date=doc_date,
            qty=qty if qty is not None else lot.initial_qty,
        )
        for lot, partner, doc_no, doc_date, qty in rows
    ]


def _processes(links: list[TraceLink]) -> list[ProcessRef]:
    """Bağlardan üretim emirleri ve parçalamalar (her belge bir kez, girdi ve çıktı lotlarıyla)."""
    grouped: dict[tuple[LinkProcess, str | None], tuple[list[str], list[str]]] = {}
    for link in links:
        inputs, outputs = grouped.setdefault((link.process, link.doc_no), ([], []))
        if link.parent_lot_no not in inputs:
            inputs.append(link.parent_lot_no)
        if link.child_lot_no not in outputs:
            outputs.append(link.child_lot_no)
    return [
        ProcessRef(process=process, doc_no=doc_no, input_lots=inputs, output_lots=outputs)
        for (process, doc_no), (inputs, outputs) in grouped.items()
    ]


def _lot_numbers(session: Session, lot_ids: Collection[int]) -> dict[int, str]:
    return {
        lot_id: lot_no
        for lot_id, lot_no in session.execute(select(Lot.id, Lot.lot_no).where(Lot.id.in_(lot_ids)))
    }


def _contact(partner: Partner) -> Contact:
    return Contact(
        person=partner.contact_person, phone=partner.phone, email=partner.email, address=partner.address
    )
