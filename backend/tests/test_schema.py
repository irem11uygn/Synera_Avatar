"""Şema ve veritabanı düzeyindeki korumalar (data_model.md, ADR-008)."""

from datetime import date
from decimal import Decimal

import pytest
from alembic import command
from sqlalchemy import delete, inspect, select, update
from sqlalchemy.exc import DBAPIError

from app.models import Partner, Purchase, PurchaseLine, StockBalance, StockMovement, SyncCounter, Warehouse
from app.models.enums import DocType, MovementType
from tests.helpers import alembic_config, by_code

EXPECTED_TABLES = {
    "users", "sessions", "products", "partners", "warehouses", "number_sequences",
    "lots", "lot_links", "stock_movements", "stock_balances",
    "purchases", "purchase_lines", "purchase_costs",
    "production_orders", "production_inputs",
    "cutting_recipes", "cutting_recipe_lines", "cuttings", "cutting_outputs",
    "sales", "sale_lines", "customer_returns", "onward_deliveries",
    "transfers", "transfer_lines", "adjustments",
    "recalls", "recall_lots", "alerts",
    "ai_forecasts", "sync_counter",
}  # fmt: skip


def test_migration_creates_all_31_tables(engine):
    assert len(EXPECTED_TABLES) == 31
    assert set(inspect(engine).get_table_names()) == EXPECTED_TABLES | {"alembic_version"}


def test_models_and_migration_are_in_sync(engine):
    """Modellerde göçe yansımamış bir değişiklik varsa Alembic hata verir."""
    command.check(alembic_config())


def test_stock_movement_cannot_be_updated(session, make_movement):
    movement = make_movement()
    with pytest.raises(DBAPIError, match="degistirilemez"), session.begin_nested():
        session.execute(update(StockMovement).where(StockMovement.id == movement.id).values(note="x"))


def test_stock_movement_cannot_be_deleted(session, make_movement):
    movement = make_movement()
    with pytest.raises(DBAPIError, match="silinemez"), session.begin_nested():
        session.execute(delete(StockMovement).where(StockMovement.id == movement.id))


def test_stock_movement_requires_nonzero_quantity(session, make_lot):
    lot = make_lot()
    movement = StockMovement(
        type=MovementType.ALIS_GIRIS,
        lot_id=lot.id,
        product_id=lot.product_id,
        warehouse_id=by_code(session, Warehouse, "ANA").id,
        qty=Decimal("0"),
        value=Decimal("0"),
        doc_type=DocType.ALIS,
        doc_id=1,
    )
    with pytest.raises(DBAPIError, match="qty_nonzero"), session.begin_nested():
        session.add(movement)
        session.flush()


def test_stock_balance_cannot_be_negative(session, make_lot):
    lot = make_lot()
    balance = StockBalance(
        lot_id=lot.id, warehouse_id=by_code(session, Warehouse, "ANA").id, qty=Decimal("-1")
    )
    with pytest.raises(DBAPIError, match="qty_nonnegative"), session.begin_nested():
        session.add(balance)
        session.flush()


def test_lot_number_is_unique(session, make_lot):
    make_lot(lot_no="TEST-ET-1")
    with pytest.raises(DBAPIError, match="Duplicate entry"), session.begin_nested():
        make_lot(lot_no="TEST-ET-1")


def _purchase_line(session, lot, note):
    purchase = Purchase(
        doc_no="FAT-1", supplier_id=by_code(session, Partner, "TED-KUZU").id, doc_date=date(2026, 10, 24)
    )
    session.add(purchase)
    session.flush()
    return PurchaseLine(
        purchase_id=purchase.id,
        product_id=lot.product_id,
        lot_id=lot.id,
        qty=Decimal("25"),
        unit_price=Decimal("11.50"),
        computed_amount=Decimal("287.50"),
        invoice_amount=Decimal("351.00"),
        discrepancy_note=note,
    )


def test_purchase_amount_mismatch_requires_note(session, make_lot):
    """FR-207 / AT-05: 25 kg × 11,50 € = 287,50 € ≠ 351,00 € → açıklamasız kayıt reddedilir."""
    lot = make_lot(lot_no="TEST-KUZU-1", product_code="KUZU-BUTUN", qty="25", value="351.00")
    line = _purchase_line(session, lot, note=None)
    with pytest.raises(DBAPIError, match="mismatch_needs_note"), session.begin_nested():
        session.add(line)
        session.flush()


def test_purchase_amount_mismatch_accepted_with_note(session, make_lot):
    lot = make_lot(lot_no="TEST-KUZU-1", product_code="KUZU-BUTUN", qty="25", value="351.00")
    session.add(_purchase_line(session, lot, note="63,50 € kesim ve nakliye dahil"))
    session.flush()


def test_sync_counter_has_exactly_one_row(session):
    counters = session.scalars(select(SyncCounter)).all()
    assert [c.id for c in counters] == [1]
    assert counters[0].value > 0  # örnek kayıtlar yüklenirken değişiklik numaraları dağıtıldı
    with pytest.raises(DBAPIError, match="single_row"), session.begin_nested():
        session.add(SyncCounter(id=2, value=0))
        session.flush()
