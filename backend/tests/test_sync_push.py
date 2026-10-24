"""Android satışlarının sunucuya gönderimi (FR-401, FR-403, FR-405; AT-08 cihaz kısmı, AT-11, AT-12)."""

from decimal import Decimal as D
from uuid import uuid4

import pytest
from sqlalchemy import func, select

from app.models import Alert, Partner, Product, Sale, SaleLine, StockBalance, StockMovement, Warehouse
from app.models.enums import DocType, LotOrigin, LotStatus, MovementType
from app.services.integrity import check_invariants
from app.services.ledger import create_lot, post_transfer
from tests.helpers import auth_header, by_code, lot_by_no

PUSH = "/api/v1/sync/push"


@pytest.fixture
def seller(client):
    return auth_header(client, "satis1", "satis123")


@pytest.fixture
def van(session) -> Warehouse:
    return by_code(session, Warehouse, "ARAC-01")


def load_van(session, van, lot_no="ET-2026-001", qty="10") -> None:
    post_transfer(
        session,
        lot_id=lot_by_no(session, lot_no).id,
        from_warehouse_id=by_code(session, Warehouse, "ANA").id,
        to_warehouse_id=van.id,
        qty=D(qty),
        doc_id=1,
    )


def sale(session, van, *, qty="4", lot_no="ET-2026-001", customer="M-A", price="12.00", uuid=None) -> dict:
    return {
        "client_uuid": uuid or str(uuid4()),
        "customer_id": by_code(session, Partner, customer).id,
        "warehouse_id": van.id,
        "sold_at": "2026-10-27T10:12:00+03:00",
        "lines": [{"lot_no": lot_no, "qty": qty, "unit_price": price}],
    }


def push(client, seller, *sales, status=200) -> list[dict]:
    response = client.post(PUSH, json={"device_id": "arac-01-test", "sales": list(sales)}, headers=seller)
    assert response.status_code == status, response.text
    return response.json()["results"] if status == 200 else response.json()


def van_qty(session, van, lot_no="ET-2026-001") -> D:
    balance = session.get(StockBalance, (lot_by_no(session, lot_no).id, van.id))
    return balance.qty if balance else D(0)


def test_sale_line_is_one_lot_and_one_movement(client, seller, session, van):
    load_van(session, van)
    [result] = push(client, seller, sale(session, van))
    assert (result["status"], result["sale_no"], result["warnings"], result["error"]) == (
        "ACCEPTED",
        "SAT-2026-0101",
        [],
        None,
    )
    assert van_qty(session, van) == D("6")
    line = session.scalars(select(SaleLine)).one()
    movement = session.get(StockMovement, line.stock_movement_id)
    assert (movement.type, movement.qty, movement.doc_type) == (MovementType.SATIS, D("-4"), DocType.SATIS)
    assert (line.amount, line.cost_amount) == (D("48.00"), D("38.80"))  # 4 × 12,00 ve 4 × 9,70
    stored = session.scalars(select(Sale)).one()
    assert (stored.device_id, stored.sold_at.hour) == ("arac-01-test", 7)  # cihaz saati UTC'ye çevrildi
    assert all(r.ok for r in check_invariants(session))


def test_same_sale_sent_twice_is_recorded_once(client, seller, session, van):
    """AT-11: bağlantı koptu, cihaz aynı satışı yeniden gönderdi → tek satış, tek hareket."""
    load_van(session, van)
    payload = sale(session, van)
    first = push(client, seller, payload)[0]
    second = push(client, seller, payload)[0]
    assert (second["status"], second["sale_no"]) == ("DUPLICATE", first["sale_no"])
    assert session.scalar(select(func.count()).select_from(Sale)) == 1
    assert session.scalar(select(func.count()).where(StockMovement.type == MovementType.SATIS)) == 1
    assert van_qty(session, van) == D("6")


def test_rejected_sale_does_not_stop_the_others(client, seller, session, van):
    load_van(session, van)
    too_much, fine = sale(session, van, qty="20"), sale(session, van, qty="2")
    rejected, accepted = push(client, seller, too_much, fine)
    assert (rejected["status"], rejected["error"]["code"]) == ("REJECTED", "INSUFFICIENT_STOCK")
    assert rejected["sale_no"] is None
    assert (accepted["status"], accepted["sale_no"]) == (
        "ACCEPTED",
        "SAT-2026-0101",
    )  # numara boşa harcanmadı
    assert van_qty(session, van) == D("8")


def test_offline_sale_of_recalled_lot_is_kept_and_flagged(client, seller, session, van):
    """AT-12: cihaz çevrimdışıyken lot bloke edildi; satış kaydedilir, ihlal işaretlenir, uyarı düşer."""
    load_van(session, van)
    lot_by_no(session, "ET-2026-001").status = LotStatus.BLOKE
    session.flush()
    [result] = push(client, seller, sale(session, van))
    assert result["status"] == "ACCEPTED_WITH_WARNING"
    assert "ET-2026-001" in result["warnings"][0]
    assert session.scalars(select(Sale)).one().recall_violation is True
    alert = session.scalars(select(Alert)).one()
    assert alert.kind == "GERI_CAGIRMA_IHLALI"
    assert "ET-2026-001 lotundan 4 kg Market A" in alert.message
    assert van_qty(session, van) == D("6")


def test_invalid_sales_are_rejected_with_reason(client, seller, session, van):
    load_van(session, van)
    sucuk = create_lot(
        session,
        lot_no="TEST-SUC-1",
        product_id=by_code(session, Product, "NARIN-SUCUK").id,
        origin=LotOrigin.URETIM,
        qty=D("10"),
        value=D("181.59"),
        warehouse_id=van.id,
        movement_type=MovementType.URETIM_GIRIS,
        doc_type=DocType.URETIM,
        doc_id=1,
    )
    supplier = sale(session, van, customer="TED-ET")
    half_package = sale(session, van, lot_no=sucuk.lot_no, qty="1.5", price="24.90")
    unknown_lot = sale(session, van, lot_no="YOK-1")
    results = push(client, seller, supplier, half_package, unknown_lot)
    assert [(r["status"], r["error"]["code"]) for r in results] == [
        ("REJECTED", "VALIDATION_ERROR"),
        ("REJECTED", "VALIDATION_ERROR"),
        ("REJECTED", "NOT_FOUND"),
    ]
    assert "1,5 adet olamaz" in results[1]["error"]["message"]
    assert session.scalar(select(func.count()).select_from(Sale)) == 0


def test_sales_only_from_own_van_and_only_by_sales_users(client, seller, session, van):
    load_van(session, van)
    main = by_code(session, Warehouse, "ANA")
    error = push(client, seller, {**sale(session, van), "warehouse_id": main.id}, status=403)
    assert error["error"]["code"] == "FORBIDDEN"
    admin = auth_header(client, "yonetici", "yonetici123")
    response = client.post(PUSH, json={"sales": []}, headers=admin)
    assert response.status_code == 403


def test_pull_after_push_shows_new_van_stock(client, seller, session, van):
    """Senkron sonrası cihaz ve sunucu stokları eşit (FR-405)."""
    load_van(session, van)
    since = client.get("/api/v1/sync/pull", params={"since": 0}, headers=seller).json()["next_since"]
    push(client, seller, sale(session, van, qty="3"))
    body = client.get("/api/v1/sync/pull", params={"since": since}, headers=seller).json()
    assert body["stock"] == [{"lot_id": lot_by_no(session, "ET-2026-001").id, "qty": "7.000"}]


def test_manager_sees_sales_with_cost(client, seller, session, van):
    load_van(session, van)
    push(client, seller, sale(session, van))
    admin = auth_header(client, "yonetici", "yonetici123")
    [listed] = client.get("/api/v1/sales", headers=admin).json()
    assert (listed["sale_no"], listed["customer_name"], listed["channel"]) == (
        "SAT-2026-0101",
        "Market A",
        "ANDROID",
    )
    assert (D(listed["total_amount"]), D(listed["total_cost"])) == (D("48.00"), D("38.80"))
    assert listed["sold_at"].endswith("Z")
