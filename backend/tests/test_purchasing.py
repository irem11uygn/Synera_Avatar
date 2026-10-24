"""Hammadde alışı (FR-102, FR-203, FR-207, AT-05)."""

from datetime import date
from decimal import Decimal as D

import pytest
from sqlalchemy import select

from app.errors import AmountMismatchNoteRequired, DuplicateLotNo, InvalidInput
from app.models import Lot, Partner, Product, PurchaseCost, PurchaseLine, Warehouse
from app.models.enums import PurchaseCostKind
from app.services.purchasing import ExtraCost, PurchaseLineInput, create_purchase
from tests.helpers import by_code, lot_by_no


def buy(session, *lines: PurchaseLineInput, supplier: str = "TED-KUZU"):
    return create_purchase(
        session,
        supplier_id=by_code(session, Partner, supplier).id,
        doc_no="FAT-TEST-1",
        doc_date=date(2026, 10, 25),
        warehouse_id=by_code(session, Warehouse, "ANA").id,
        lines=list(lines),
    )


def lamb(session, **kwargs) -> PurchaseLineInput:
    return PurchaseLineInput(
        product_id=by_code(session, Product, "KUZU-BUTUN").id,
        lot_no="KUZU-2026-013",
        qty=D("25"),
        unit_price=D("11.50"),
        **kwargs,
    )


def test_at05_invoice_351_without_explanation_is_rejected(session):
    with pytest.raises(AmountMismatchNoteRequired) as error, session.begin_nested():
        buy(session, lamb(session, invoice_amount=D("351.00")))
    assert error.value.details == {
        "lot_no": "KUZU-2026-013",
        "computed_amount": D("287.50"),
        "invoice_amount": D("351.00"),
    }
    assert session.scalar(select(Lot.id).where(Lot.lot_no == "KUZU-2026-013")) is None


def test_at05_invoice_351_with_explanation_is_accepted(session):
    buy(
        session, lamb(session, invoice_amount=D("351.00"), discrepancy_note="Kesim ve nakliye faturaya dahil")
    )
    lot = lot_by_no(session, "KUZU-2026-013")
    assert (lot.remaining_qty, lot.remaining_value, lot.unit_cost) == (D("25"), D("351.00"), D("14.040000"))


def test_extra_cost_lines_make_the_real_total_cost(session):
    """Gerçek toplam alış maliyeti = mal bedeli 287,50 + kesim 40,00 + nakliye 23,50 = 351,00 (FR-203)."""
    buy(
        session,
        lamb(
            session,
            extra_costs=[
                ExtraCost(PurchaseCostKind.KESIM, D("40.00")),
                ExtraCost(PurchaseCostKind.NAKLIYE, D("23.50")),
            ],
        ),
    )
    lot = lot_by_no(session, "KUZU-2026-013")
    line = session.scalars(select(PurchaseLine).where(PurchaseLine.lot_id == lot.id)).one()
    costs = session.scalars(select(PurchaseCost.amount).where(PurchaseCost.purchase_line_id == line.id)).all()
    assert (line.computed_amount, line.invoice_amount, sorted(costs)) == (
        D("287.50"),
        D("287.50"),
        [D("23.50"), D("40.00")],
    )
    assert lot.initial_value == D("351.00")


def test_seeded_lamb_lot_is_351(session):
    assert lot_by_no(session, "KUZU-2026-012").initial_value == D("351.00")


def test_expiry_defaults_to_purchase_date_plus_shelf_life(session):
    buy(session, lamb(session))
    assert lot_by_no(session, "KUZU-2026-013").expiry_date == date(2026, 10, 30)  # 25 Ekim + 5 gün


def test_lot_records_its_supplier(session):
    buy(session, lamb(session))
    assert lot_by_no(session, "KUZU-2026-013").supplier_id == by_code(session, Partner, "TED-KUZU").id


def test_only_suppliers_can_sell_to_us(session):
    with pytest.raises(InvalidInput, match="tedarikçi"):
        buy(session, lamb(session), supplier="M-A")


def test_existing_lot_number_is_rejected(session):
    with pytest.raises(DuplicateLotNo):
        buy(
            session,
            PurchaseLineInput(
                product_id=by_code(session, Product, "ET").id,
                lot_no="ET-2026-001",
                qty=D("1"),
                unit_price=D("9.70"),
            ),
            supplier="TED-ET",
        )
