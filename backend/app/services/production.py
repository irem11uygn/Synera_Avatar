"""Dış hizmetle üretim — Görev 1 (FR-105…FR-111, architecture.md §4.1).

Akış: emir (TASLAK) → hammadde sevki (SEVK_EDILDI) → mamul kabulü (TAMAMLANDI).
Hammaddeler işletmenindir: sevk satış değil, dış üretici deposuna transferdir. Mamul lotunun değeri
= tüketilen hammaddelerin gerçek lot maliyeti + hizmet faturası; EKP = değer / teslim alınan miktar.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import timedelta
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.domain.costing import ProductionCost, Profitability, line_amount, production_cost, profitability
from app.domain.money import round_percent, tr_number
from app.errors import AmountMismatchNoteRequired, InvalidInput, InvalidState, LotBlocked, NotFound
from app.models import Lot, Partner, Product, ProductionInput, ProductionOrder, StockMovement, Warehouse
from app.models.enums import (
    BaseUnit,
    DocType,
    LinkProcess,
    LotOrigin,
    LotStatus,
    MovementType,
    ProductionKind,
    ProductionStatus,
    ProductKind,
    TransferReason,
    WarehouseKind,
)
from app.models.types import utcnow
from app.services import ai
from app.services.ledger import create_lot, post_movement
from app.services.lookups import get_or_404, main_warehouse
from app.services.lot_graph import link_lots
from app.services.numbering import next_document_no
from app.services.transfers import TransferLineInput, create_transfer


@dataclass(frozen=True)
class PlannedInput:
    lot_id: int
    qty: Decimal


@dataclass(frozen=True)
class InputResult:
    lot_id: int
    consumed_qty: Decimal
    returned_qty: Decimal


def create_order(
    session: Session,
    *,
    subcontractor_id: int,
    output_product_id: int,
    planned_qty: Decimal,
    inputs: Sequence[PlannedInput],
    service_unit_price: Decimal | None = None,
    user_id: int | None = None,
) -> ProductionOrder:
    subcontractor = get_or_404(session, Partner, subcontractor_id, "Dış üretici")
    if not subcontractor.is_subcontractor:
        raise InvalidInput("Seçilen cari dış üretici olarak tanımlı değil.", partner_id=subcontractor_id)
    warehouse = session.scalars(
        select(Warehouse).where(
            Warehouse.partner_id == subcontractor.id, Warehouse.kind == WarehouseKind.DIS_URETICI
        )
    ).first()
    if warehouse is None:
        raise InvalidInput(f"{subcontractor.name} için dış üretici deposu tanımlı değil.")
    product = get_or_404(session, Product, output_product_id, "Mamul")
    if product.kind != ProductKind.MAMUL:
        raise InvalidInput("Dış üretimin çıktısı mamul türünde bir ürün olmalı.", product=product.code)
    _check_quantity(product, planned_qty, "Planlanan miktar")
    if service_unit_price is not None and service_unit_price < 0:
        raise InvalidInput("Hizmet birim ücreti eksi olamaz.")
    if not inputs:
        raise InvalidInput("Emirde en az bir hammadde lotu olmalı.")
    if len({i.lot_id for i in inputs}) != len(inputs):
        raise InvalidInput("Bir lot emirde yalnız bir kez yer alabilir.")
    for item in inputs:
        lot = get_or_404(session, Lot, item.lot_id, "Hammadde lotu")
        if lot.status == LotStatus.BLOKE:
            raise LotBlocked(f"{lot.lot_no} lotu bloke; üretimde kullanılamaz.", lot_no=lot.lot_no)
        if item.qty <= 0:
            raise InvalidInput(f"{lot.lot_no}: planlanan miktar sıfırdan büyük olmalı.")

    order = ProductionOrder(
        order_no=next_document_no(session, "URT", utcnow().year),
        kind=ProductionKind.DIS_URETIM,
        subcontractor_id=subcontractor.id,
        subcontractor_warehouse_id=warehouse.id,
        output_product_id=product.id,
        planned_qty=planned_qty,
        service_unit_price=service_unit_price,
        created_by=user_id,
    )
    session.add(order)
    session.flush()
    session.add_all(ProductionInput(order_id=order.id, lot_id=i.lot_id, planned_qty=i.qty) for i in inputs)
    session.flush()
    ai.forecast_production(session, order)  # Model A tahmini kaydedilir; hata iş akışını durdurmaz
    return order


def ship_order(session: Session, order_id: int, user_id: int | None = None) -> ProductionOrder:
    """Planlanan hammaddeleri ana depodan dış üretici deposuna transfer eder."""
    order = _lock_order(session, order_id, expected=ProductionStatus.TASLAK, action="sevk")
    inputs = _inputs(session, order)
    create_transfer(
        session,
        from_warehouse_id=main_warehouse(session).id,
        to_warehouse_id=order.subcontractor_warehouse_id,
        lines=[TransferLineInput(i.lot_id, i.planned_qty) for i in inputs],
        reason=TransferReason.DIS_URETIM_SEVK,
        production_order_id=order.id,
        user_id=user_id,
    )
    for item in inputs:
        item.shipped_qty = item.planned_qty
    order.status = ProductionStatus.SEVK_EDILDI
    order.shipped_at = utcnow()
    session.flush()
    return order


def complete_order(
    session: Session,
    order_id: int,
    *,
    received_qty: Decimal,
    inputs: Sequence[InputResult],
    service_amount: Decimal | None = None,
    service_invoice_no: str | None = None,
    service_note: str | None = None,
    output_lot_no: str | None = None,
    user_id: int | None = None,
) -> ProductionOrder:
    """Mamul kabulü: iadeler, tüketim, hizmet, mamul lotu ve lot bağlantıları — tek işlemde (NFR-003)."""
    order = _lock_order(session, order_id, expected=ProductionStatus.SEVK_EDILDI, action="mamul kabulü")
    product = session.get(Product, order.output_product_id)
    assert product is not None
    _check_quantity(product, received_qty, "Teslim alınan miktar")
    rows = {row.lot_id: row for row in _inputs(session, order)}
    results = _validated_results(session, rows, inputs)
    service = _service_amount(order, received_qty, service_amount, service_note)
    main = main_warehouse(session)

    returns = [TransferLineInput(r.lot_id, r.returned_qty) for r in results if r.returned_qty > 0]
    if returns:
        create_transfer(
            session,
            from_warehouse_id=order.subcontractor_warehouse_id,
            to_warehouse_id=main.id,
            lines=returns,
            reason=TransferReason.DIS_URETIM_IADE,
            production_order_id=order.id,
            user_id=user_id,
        )
    consumed_value = Decimal(0)
    for result in results:
        rows[result.lot_id].consumed_qty = result.consumed_qty
        rows[result.lot_id].returned_qty = result.returned_qty
        if result.consumed_qty > 0:
            movement = post_movement(
                session,
                lot_id=result.lot_id,
                warehouse_id=order.subcontractor_warehouse_id,
                movement_type=MovementType.URETIM_TUKETIM,
                qty=-result.consumed_qty,
                doc_type=DocType.URETIM,
                doc_id=order.id,
                user_id=user_id,
            )
            consumed_value -= movement.value

    today = utcnow().date()
    lot = create_lot(
        session,
        lot_no=output_lot_no or _default_output_lot_no(order, product),
        product_id=product.id,
        origin=LotOrigin.URETIM,
        qty=received_qty,
        value=consumed_value + service,
        warehouse_id=main.id,
        movement_type=MovementType.URETIM_GIRIS,
        doc_type=DocType.URETIM,
        doc_id=order.id,
        produced_at=today,
        expiry_date=today + timedelta(days=product.shelf_life_days) if product.shelf_life_days else None,
        user_id=user_id,
    )
    for result in results:
        if result.consumed_qty > 0:
            link_lots(
                session,
                parent_lot_id=result.lot_id,
                child_lot_id=lot.id,
                qty=result.consumed_qty,
                process=LinkProcess.URETIM,
                process_id=order.id,
            )

    order.received_qty = received_qty
    order.service_amount = service
    order.service_invoice_no = (service_invoice_no or "").strip() or None
    order.service_note = (service_note or "").strip() or None
    order.output_lot_id = lot.id
    order.status = ProductionStatus.TAMAMLANDI
    order.completed_at = utcnow()
    session.flush()
    return order


def cancel_order(session: Session, order_id: int) -> ProductionOrder:
    order = _lock_order(session, order_id, expected=ProductionStatus.TASLAK, action="iptal")
    order.status = ProductionStatus.IPTAL
    session.flush()
    return order


# --- Okuma modeli: emir ayrıntısı (EKP, kâr/marj, verim, farklar) ---


@dataclass(frozen=True)
class InputLine:
    lot_no: str
    product_name: str
    base_unit: BaseUnit
    planned_qty: Decimal
    shipped_qty: Decimal
    consumed_qty: Decimal
    returned_qty: Decimal
    consumed_value: Decimal


@dataclass(frozen=True)
class Yield:
    output_kg: Decimal
    inputs_kg: Decimal
    main_input_kg: Decimal
    yield_total_pct: Decimal  # mamul kg / toplam tüketilen kg
    yield_main_pct: Decimal  # mamul kg / en büyük girdi kg (et bazlı verim, AS-007)


@dataclass(frozen=True)
class OrderSummary:
    order: ProductionOrder
    subcontractor: Partner
    product: Product
    output_lot_no: str | None
    inputs: list[InputLine]
    cost: ProductionCost | None
    sales: Profitability | None
    yield_: Yield | None


def order_summary(session: Session, order: ProductionOrder) -> OrderSummary:
    product = session.get(Product, order.output_product_id)
    subcontractor = session.get(Partner, order.subcontractor_id)
    assert product is not None and subcontractor is not None
    consumed_values = dict(
        session.execute(
            select(StockMovement.lot_id, -func.sum(StockMovement.value))
            .where(
                StockMovement.doc_type == DocType.URETIM,
                StockMovement.doc_id == order.id,
                StockMovement.type == MovementType.URETIM_TUKETIM,
            )
            .group_by(StockMovement.lot_id)
        ).all()
    )
    lines = []
    for row in _inputs(session, order):
        lot = session.get(Lot, row.lot_id)
        lot_product = session.get(Product, lot.product_id) if lot else None
        assert lot is not None and lot_product is not None
        lines.append(
            InputLine(
                lot_no=lot.lot_no,
                product_name=lot_product.name,
                base_unit=lot_product.base_unit,
                planned_qty=row.planned_qty,
                shipped_qty=row.shipped_qty,
                consumed_qty=row.consumed_qty,
                returned_qty=row.returned_qty,
                consumed_value=consumed_values.get(row.lot_id, Decimal("0.00")),
            )
        )

    cost = sales = yield_ = None
    output_lot = session.get(Lot, order.output_lot_id) if order.output_lot_id else None
    if (
        order.status == ProductionStatus.TAMAMLANDI
        and order.received_qty
        and order.service_amount is not None
    ):
        cost = production_cost(
            [line.consumed_value for line in lines], order.service_amount, order.received_qty
        )
        if product.sale_price:
            sales = profitability(product.sale_price, cost.ekp)
        yield_ = _yield(product, order.received_qty, lines)
    return OrderSummary(
        order=order,
        subcontractor=subcontractor,
        product=product,
        output_lot_no=output_lot.lot_no if output_lot else None,
        inputs=lines,
        cost=cost,
        sales=sales,
        yield_=yield_,
    )


def _yield(product: Product, received_qty: Decimal, lines: list[InputLine]) -> Yield | None:
    kg_inputs = [
        line.consumed_qty for line in lines if line.base_unit == BaseUnit.KG and line.consumed_qty > 0
    ]
    if not kg_inputs:
        return None
    output_kg = (
        received_qty * (product.unit_weight_kg or 1) if product.base_unit == BaseUnit.ADET else received_qty
    )
    total, main = sum(kg_inputs, Decimal(0)), max(kg_inputs)
    return Yield(
        output_kg=output_kg,
        inputs_kg=total,
        main_input_kg=main,
        yield_total_pct=round_percent(output_kg / total * 100),
        yield_main_pct=round_percent(output_kg / main * 100),
    )


# --- Yardımcılar ---


def _lock_order(
    session: Session, order_id: int, *, expected: ProductionStatus, action: str
) -> ProductionOrder:
    order = session.execute(
        select(ProductionOrder)
        .where(ProductionOrder.id == order_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    ).scalar_one_or_none()
    if order is None:
        raise NotFound("Üretim emri bulunamadı.", id=order_id)
    if order.status != expected:
        raise InvalidState(
            f"{order.order_no} emri '{order.status}' durumunda; "
            f"{action} yalnız '{expected}' durumunda yapılabilir.",
            order_no=order.order_no,
            status=order.status,
        )
    return order


def _inputs(session: Session, order: ProductionOrder) -> list[ProductionInput]:
    return list(
        session.scalars(
            select(ProductionInput).where(ProductionInput.order_id == order.id).order_by(ProductionInput.id)
        )
    )


def _validated_results(
    session: Session, rows: dict[int, ProductionInput], inputs: Sequence[InputResult]
) -> list[InputResult]:
    given = {result.lot_id: result for result in inputs}
    if len(given) != len(inputs) or set(given) != set(rows):
        raise InvalidInput(
            "Emirdeki her hammadde lotu için tüketilen ve iade edilen miktar bir kez girilmeli."
        )
    lot_nos = dict(session.execute(select(Lot.id, Lot.lot_no).where(Lot.id.in_(rows))).all())
    for lot_id, row in rows.items():
        result = given[lot_id]
        lot_no = lot_nos[lot_id]
        if result.consumed_qty < 0 or result.returned_qty < 0:
            raise InvalidInput(f"{lot_no}: tüketilen ve iade edilen miktar eksi olamaz.")
        if result.consumed_qty + result.returned_qty != row.shipped_qty:
            raise InvalidInput(
                f"{lot_no}: tüketilen ({tr_number(result.consumed_qty)}) + iade edilen "
                f"({tr_number(result.returned_qty)}) sevk edilen miktara ({tr_number(row.shipped_qty)}) "
                "eşit olmalı.",
                lot_no=lot_no,
            )
    if all(result.consumed_qty == 0 for result in inputs):
        raise InvalidInput("Mamul kabulünde en az bir hammadde tüketilmiş olmalı.")
    return [given[lot_id] for lot_id in rows]


def _service_amount(
    order: ProductionOrder, received_qty: Decimal, amount: Decimal | None, note: str | None
) -> Decimal:
    """Hizmet faturası; adet × birim ücretten farklıysa açıklama zorunlu (FR-207 ile aynı kural)."""
    suggested = (
        line_amount(received_qty, order.service_unit_price) if order.service_unit_price is not None else None
    )
    final = amount if amount is not None else suggested
    if final is None:
        raise InvalidInput("Hizmet faturası tutarı girilmeli (emirde birim hizmet ücreti yok).")
    if final < 0:
        raise InvalidInput("Hizmet faturası tutarı eksi olamaz.")
    if suggested is not None and final != suggested and not (note or "").strip():
        raise AmountMismatchNoteRequired(
            f"Hizmet faturası ({tr_number(final, 2)} €) teslim alınan miktar × birim ücretten "
            f"({tr_number(suggested, 2)} €) farklı; "
            "farkın nedenini açıklayın.",
            suggested_amount=suggested,
            invoice_amount=final,
        )
    return final


def _default_output_lot_no(order: ProductionOrder, product: Product) -> str:
    """URT-2026-045 → SUC-2026-045 (mamulün lot öneki + emrin yıl ve sırası)."""
    return f"{product.lot_prefix or product.code}-{order.order_no.split('-', 1)[1]}"


def _check_quantity(product: Product, qty: Decimal, label: str) -> None:
    if qty <= 0:
        raise InvalidInput(f"{label} sıfırdan büyük olmalı.")
    if product.base_unit == BaseUnit.ADET and qty != qty.to_integral_value():
        raise InvalidInput(f"{label}: {product.name} adet ile izlenir; tam sayı girilmeli.", qty=qty)
