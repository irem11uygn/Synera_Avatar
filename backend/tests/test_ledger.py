"""Stok defteri ve lot ağı (ADR-008; AT-01, AT-06, AT-07, AT-08, AT-10 defter düzeyinde)."""

from decimal import Decimal as D

import pytest
from sqlalchemy import func, select

from app.errors import DuplicateLotNo, InsufficientStock, InvalidInput, LotBlocked
from app.models import Lot, Product, StockBalance, StockMovement, Warehouse
from app.models.enums import DocType, LinkProcess, LotOrigin, LotStatus, MovementType
from app.services.integrity import check_invariants
from app.services.ledger import create_lot, post_movement, post_transfer, reverse_movement
from app.services.lot_graph import ancestors, descendants, link_lots
from tests.helpers import by_code, lot_by_no

RAW_LOTS = [("ET-2026-001", D("100")), ("BAH-2026-014", D("2")), ("BAG-2026-007", D("5"))]


def wh(session, code: str) -> int:
    return by_code(session, Warehouse, code).id


def balance(session, lot: Lot, code: str) -> D:
    row = session.get(StockBalance, (lot.id, wh(session, code)))
    return row.qty if row else D(0)


def sell(session, lot: Lot, qty: str, **kwargs) -> StockMovement:
    return post_movement(
        session,
        lot_id=lot.id,
        warehouse_id=wh(session, "ARAC-01"),
        movement_type=MovementType.SATIS,
        qty=-D(qty),
        doc_type=DocType.SATIS,
        doc_id=1,
        **kwargs,
    )


@pytest.fixture
def sucuk(session) -> Lot:
    """Şartname senaryosu defter düzeyinde: sevk → tüketim → SUC-2026-045 (85 paket) → araç deposu."""
    consumed = D(0)
    order_id = 45
    sucuk_product = by_code(session, Product, "NARIN-SUCUK")
    parents = []
    for lot_no, qty in RAW_LOTS:
        lot = lot_by_no(session, lot_no)
        post_transfer(
            session,
            lot_id=lot.id,
            from_warehouse_id=wh(session, "ANA"),
            to_warehouse_id=wh(session, "DIS-FSN-01"),
            qty=qty,
            doc_id=1,
        )
        movement = post_movement(
            session,
            lot_id=lot.id,
            warehouse_id=wh(session, "DIS-FSN-01"),
            movement_type=MovementType.URETIM_TUKETIM,
            qty=-qty,
            doc_type=DocType.URETIM,
            doc_id=order_id,
        )
        consumed -= movement.value
        parents.append((lot, qty))
    lot = create_lot(
        session,
        lot_no="SUC-2026-045",
        product_id=sucuk_product.id,
        origin=LotOrigin.URETIM,
        qty=D("85"),
        value=consumed + D("467.50"),
        warehouse_id=wh(session, "ANA"),
        movement_type=MovementType.URETIM_GIRIS,
        doc_type=DocType.URETIM,
        doc_id=order_id,
    )
    for parent, qty in parents:
        link_lots(
            session,
            parent_lot_id=parent.id,
            child_lot_id=lot.id,
            qty=qty,
            process=LinkProcess.URETIM,
            process_id=45,
        )
    post_transfer(
        session,
        lot_id=lot.id,
        from_warehouse_id=wh(session, "ANA"),
        to_warehouse_id=wh(session, "ARAC-01"),
        qty=D("85"),
        doc_id=2,
    )
    return lot


def test_seeded_purchase_created_lot_and_entry_movement(session):
    lot = lot_by_no(session, "ET-2026-001")
    assert (lot.remaining_qty, lot.remaining_value, lot.unit_cost) == (D("100"), D("970.00"), D("9.700000"))
    assert balance(session, lot, "ANA") == D("100")
    movements = session.scalars(select(StockMovement).where(StockMovement.lot_id == lot.id)).all()
    assert [(m.type, m.qty, m.value) for m in movements] == [(MovementType.ALIS_GIRIS, D("100"), D("970.00"))]


def test_at01_sucuk_lot_value_is_exact_total(session, sucuk):
    assert sucuk.initial_value == D("1543.50")
    assert sucuk.unit_cost == D("18.158824")
    for lot_no, _ in RAW_LOTS:
        assert (lot_by_no(session, lot_no).remaining_qty, lot_by_no(session, lot_no).remaining_value) == (
            D("0"),
            D("0.00"),
        )


def test_transfer_moves_stock_but_not_value(session, sucuk):
    assert balance(session, sucuk, "ANA") == D("0")
    assert balance(session, sucuk, "ARAC-01") == D("85")
    assert sucuk.remaining_value == D("1543.50")
    transfer_values = session.scalars(
        select(StockMovement.value).where(
            StockMovement.lot_id == sucuk.id,
            StockMovement.type.in_([MovementType.TRANSFER_CIKIS, MovementType.TRANSFER_GIRIS]),
        )
    ).all()
    assert transfer_values == [D("0.00"), D("0.00")]


def test_sales_30_25_30_cost_exactly_the_lot_value(session, sucuk):
    costs = [-sell(session, sucuk, qty).value for qty in ("30", "25", "30")]
    assert costs == [D("544.76"), D("453.97"), D("544.77")]
    assert (sucuk.remaining_qty, sucuk.remaining_value) == (D("0"), D("0.00"))


def test_overselling_is_rejected_and_writes_nothing(session, sucuk):
    before = session.scalar(select(func.count()).select_from(StockMovement))
    with pytest.raises(InsufficientStock), session.begin_nested():
        sell(session, sucuk, "86")
    assert session.scalar(select(func.count()).select_from(StockMovement)) == before
    assert balance(session, sucuk, "ARAC-01") == D("85")


def test_stock_must_be_in_the_selling_warehouse(session):
    """ET-2026-001 ana depoda; araç deposundan satılamaz."""
    with pytest.raises(InsufficientStock, match="bu depoda"), session.begin_nested():
        sell(session, lot_by_no(session, "ET-2026-001"), "1")


def test_at08_blocked_lot_cannot_be_sold_or_moved(session, sucuk):
    sucuk.status = LotStatus.BLOKE
    session.flush()
    with pytest.raises(LotBlocked), session.begin_nested():
        sell(session, sucuk, "1")
    with pytest.raises(LotBlocked), session.begin_nested():
        post_transfer(
            session,
            lot_id=sucuk.id,
            from_warehouse_id=wh(session, "ARAC-01"),
            to_warehouse_id=wh(session, "ANA"),
            qty=D("1"),
            doc_id=3,
        )


def test_offline_android_sale_of_blocked_lot_is_recorded_when_explicitly_allowed(session, sucuk):
    """ADR-004: çevrimdışı yapılmış satış kaydedilir (ihlal ayrıca işaretlenir)."""
    sucuk.status = LotStatus.BLOKE
    session.flush()
    assert sell(session, sucuk, "2", allow_blocked=True).qty == D("-2")


def test_blocked_lot_can_still_be_scrapped(session, sucuk):
    sucuk.status = LotStatus.BLOKE
    session.flush()
    post_movement(
        session,
        lot_id=sucuk.id,
        warehouse_id=wh(session, "ARAC-01"),
        movement_type=MovementType.FIRE,
        qty=-D("85"),
        doc_type=DocType.DUZELTME,
        doc_id=1,
    )
    assert (sucuk.remaining_qty, sucuk.remaining_value) == (D("0"), D("0.00"))


def test_at06_at07_lot_network_forward_and_backward(session, sucuk):
    et = lot_by_no(session, "ET-2026-001")
    assert descendants(session, et.id) == {et.id: 0, sucuk.id: 1}
    raw_ids = {lot_by_no(session, lot_no).id for lot_no, _ in RAW_LOTS}
    assert ancestors(session, sucuk.id) == {sucuk.id: 0, **dict.fromkeys(raw_ids, 1)}


def test_reversal_restores_lot_exactly(session, sucuk):
    movement = sell(session, sucuk, "30")
    reversal = reverse_movement(session, movement.id, reason="Yanlış müşteri")
    assert (reversal.qty, reversal.value, reversal.reversal_of_id) == (D("30.000"), D("544.76"), movement.id)
    assert (sucuk.remaining_qty, sucuk.remaining_value) == (D("85"), D("1543.50"))
    with pytest.raises(InvalidInput, match="zaten"):
        reverse_movement(session, movement.id, reason="tekrar")


def test_wrong_direction_and_manual_outflow_value_are_rejected(session, sucuk):
    with pytest.raises(InvalidInput, match="negatif"):
        sell(session, sucuk, "-1")
    with pytest.raises(InvalidInput, match="hesaplanır"):
        sell(session, sucuk, "1", value=D("-1.00"))


def test_duplicate_lot_number_is_rejected(session):
    with pytest.raises(DuplicateLotNo):
        create_lot(
            session,
            lot_no="ET-2026-001",
            product_id=by_code(session, Product, "ET").id,
            origin=LotOrigin.ALIS,
            qty=D("1"),
            value=D("9.70"),
            warehouse_id=wh(session, "ANA"),
            movement_type=MovementType.ALIS_GIRIS,
            doc_type=DocType.ALIS,
            doc_id=1,
        )


def test_lot_cannot_be_linked_to_itself(session, sucuk):
    with pytest.raises(InvalidInput):
        link_lots(
            session,
            parent_lot_id=sucuk.id,
            child_lot_id=sucuk.id,
            qty=D("1"),
            process=LinkProcess.URETIM,
            process_id=1,
        )


def test_changed_lots_and_balances_get_new_change_numbers(session, sucuk):
    """Android senkronizasyonu bu numaralarla yalnız değişenleri çeker (ADR-004)."""
    arac_balance = session.get(StockBalance, (sucuk.id, wh(session, "ARAC-01")))
    lot_seq, balance_seq = sucuk.change_seq, arac_balance.change_seq
    assert lot_seq > 0 and balance_seq > 0
    sell(session, sucuk, "1")
    assert sucuk.change_seq > lot_seq
    assert arac_balance.change_seq > balance_seq


def test_invariants_hold_after_full_scenario(session, sucuk):
    for qty in ("30", "25", "30"):
        sell(session, sucuk, qty)
    assert [(r.code, r.violations) for r in check_invariants(session) if not r.ok] == []
