"""Bütünlük denetimi (FR-607, AT-10): değişmezler I-1…I-8."""

from decimal import Decimal as D

from app.models import StockMovement, Warehouse
from app.models.enums import DocType, MovementType
from app.services.integrity import check_invariants
from tests.helpers import by_code, lot_by_no


def test_all_invariants_hold_on_seeded_data(session):
    results = check_invariants(session)
    assert [r.code for r in results] == [f"I-{i}" for i in range(1, 9)]
    assert all(r.ok for r in results), [(r.code, r.violations) for r in results if not r.ok]


def test_movement_written_around_the_ledger_is_detected(session):
    """Defter servisini atlayan bir yazım özetleri bozar; denetim bunu yakalar."""
    lot = lot_by_no(session, "ET-2026-001")
    session.add(
        StockMovement(
            type=MovementType.ALIS_GIRIS,
            lot_id=lot.id,
            product_id=lot.product_id,
            warehouse_id=by_code(session, Warehouse, "ANA").id,
            qty=D("5"),
            value=D("48.50"),
            doc_type=DocType.ALIS,
            doc_id=99,
        )
    )
    session.flush()
    failed = {r.code: r.violations for r in check_invariants(session) if not r.ok}
    assert set(failed) == {"I-1", "I-2", "I-3"}
    assert all("ET-2026-001" in v for violations in failed.values() for v in violations)
