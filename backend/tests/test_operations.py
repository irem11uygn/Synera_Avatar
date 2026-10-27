"""Gerçek kullanım: mağaza satışı, ödeme türü, son kullanma tarihi kuralı, gün sonu, sayım, ana sayfa."""

from datetime import timedelta
from decimal import Decimal as D
from uuid import uuid4

import pytest
from sqlalchemy import select

from app.domain.clock import business_today
from app.models import Alert, Partner, Product, Sale, StockBalance, Warehouse
from app.models.enums import AlertKind
from app.services.integrity import check_invariants
from app.services.ledger import post_transfer
from tests.helpers import auth_header, by_code, lot_by_no, make_lot, store_sale

API = "/api/v1"


@pytest.fixture
def store(client):
    return auth_header(client, "magaza1", "magaza123")


@pytest.fixture
def admin(client):
    return auth_header(client, "yonetici", "yonetici123")


# --- Mağaza satışı ---


def test_store_sale_uses_list_price_and_records_payment(client, store, session):
    make_lot(session, "SUC-T-1")
    response = store_sale(client, store, session, {"lot_no": "SUC-T-1", "qty": "3"})
    assert response.status_code == 201, response.text
    sale = response.json()
    assert (sale["channel"], sale["payment_method"], sale["seller_name"]) == (
        "WEB",
        "KART",
        "Demo Mağaza Kasası",
    )
    assert D(sale["lines"][0]["unit_price"]) == D("24.90")  # ürün kartındaki liste fiyatı
    assert D(sale["total_amount"]) == D("74.70")
    assert session.get(
        StockBalance, (lot_by_no(session, "SUC-T-1").id, by_code(session, Warehouse, "ANA").id)
    ).qty == D("37")
    assert [r for r in check_invariants(session) if not r.ok] == []


def test_store_cannot_sell_expired_lot(client, store, session):
    make_lot(session, "SUC-T-OLD", days_left=-1)
    response = store_sale(client, store, session, {"lot_no": "SUC-T-OLD", "qty": "1", "unit_price": "20"})
    assert response.status_code == 422
    assert "son kullanma tarihi geçmiş" in response.json()["error"]["message"]


def test_store_cannot_sell_blocked_lot(client, store, admin, session):
    make_lot(session, "SUC-T-BLK")
    recall = client.post(f"{API}/recalls", json={"lot_no": "SUC-T-BLK", "reason": "Deneme"}, headers=admin)
    assert recall.status_code == 201, recall.text
    response = store_sale(client, store, session, {"lot_no": "SUC-T-BLK", "qty": "1"})
    assert (response.status_code, response.json()["error"]["code"]) == (409, "LOT_BLOCKED")


def test_store_sale_only_from_main_warehouse(client, store, session):
    make_lot(session, "SUC-T-VAN", warehouse="ARAC-01")
    response = store_sale(client, store, session, {"lot_no": "SUC-T-VAN", "qty": "1"}, warehouse="ARAC-01")
    assert response.status_code == 422
    assert "telefondan" in response.json()["error"]["message"]


def test_store_sale_without_any_price_is_rejected(client, store, session):
    make_lot(session, "ET-T-1", product="ET", qty="10", value="97.00")  # hammaddenin liste fiyatı yok
    response = store_sale(client, store, session, {"lot_no": "ET-T-1", "qty": "1"})
    assert response.status_code == 422
    assert "fiyat" in response.json()["error"]["message"]


# --- Araç satışı: çevrimdışı SKT ihlali ve ödeme türü ---


def test_offline_sale_of_expired_lot_is_kept_with_warning(client, session):
    seller = auth_header(client, "satis1", "satis123")
    van = by_code(session, Warehouse, "ARAC-01")
    make_lot(session, "SUC-T-VANOLD", days_left=-2)
    post_transfer(
        session,
        lot_id=lot_by_no(session, "SUC-T-VANOLD").id,
        from_warehouse_id=by_code(session, Warehouse, "ANA").id,
        to_warehouse_id=van.id,
        qty=D("5"),
        doc_id=1,
    )
    body = {
        "client_uuid": str(uuid4()),
        "customer_id": by_code(session, Partner, "M-B").id,
        "warehouse_id": van.id,
        "sold_at": f"{business_today().isoformat()}T10:00:00+03:00",
        "payment_method": "NAKIT",
        "lines": [{"lot_no": "SUC-T-VANOLD", "qty": "2", "unit_price": "24.90"}],
    }
    response = client.post(f"{API}/sync/push", json={"sales": [body]}, headers=seller)
    result = response.json()["results"][0]
    assert result["status"] == "ACCEPTED_WITH_WARNING", result
    assert "Son kullanma tarihi geçmiş" in result["warnings"][0]
    sale = session.scalars(select(Sale).where(Sale.sale_no == result["sale_no"])).one()
    assert sale.payment_method == "NAKIT"
    kinds = session.scalars(select(Alert.kind).where(Alert.ref_type == "SALE", Alert.ref_id == sale.id)).all()
    assert kinds == [AlertKind.SKT_IHLALI]


# --- Gün sonu ---


def test_day_end_totals_by_payment_and_seller(client, store, admin, session):
    make_lot(session, "SUC-T-DAY")
    first = store_sale(client, store, session, {"lot_no": "SUC-T-DAY", "qty": "2"}, payment="NAKIT").json()
    store_sale(
        client, store, session, {"lot_no": "SUC-T-DAY", "qty": "4", "unit_price": "25.00"}, payment="KART"
    )
    refund = client.post(
        f"{API}/returns", json={"sale_line_id": first["lines"][0]["id"], "qty": "1"}, headers=store
    )
    assert refund.status_code == 201, refund.text

    report = client.get(f"{API}/day-end", headers=store).json()
    totals = {row["key"]: (row["sale_count"], D(row["amount"])) for row in report["by_payment"]}
    assert totals["NAKIT"] == (1, D("49.80"))
    assert totals["KART"] == (1, D("100.00"))
    assert D(report["refund_amount"]) == D("24.90")
    assert D(report["net_amount"]) == D(report["sales_amount"]) - D("24.90")
    sellers = {row["key"]: row["sale_count"] for row in report["by_seller"]}
    assert sellers["Demo Mağaza Kasası"] == 2
    yesterday = (business_today() - timedelta(days=1)).isoformat()
    assert client.get(f"{API}/day-end?day={yesterday}", headers=admin).json()["sale_count"] == 0


def test_seller_day_end_shows_own_sales_and_van_stock(client, session):
    seller = auth_header(client, "satis1", "satis123")
    report = client.get(f"{API}/sync/day-end", headers=seller)
    assert report.status_code == 200, report.text
    assert report.json()["sale_count"] == 0
    assert isinstance(report.json()["stock_left"], list)


# --- Sayım ---


def test_count_shortage_becomes_waste_and_surplus_is_reported(client, session):
    depot = auth_header(client, "depo1", "depo1234")
    make_lot(session, "SUC-T-CNT1", qty="10", value="75.00")
    make_lot(session, "SUC-T-CNT2", qty="10", value="75.00")
    ana = by_code(session, Warehouse, "ANA")
    body = {
        "warehouse_id": ana.id,
        "note": "Ay sonu sayımı",
        "lines": [
            {"lot_no": "SUC-T-CNT1", "counted_qty": "8"},
            {"lot_no": "SUC-T-CNT2", "counted_qty": "11"},
        ],
    }
    response = client.post(f"{API}/stock-counts", json=body, headers=depot)
    assert response.status_code == 201, response.text
    count = response.json()
    lines = {line["lot_no"]: line for line in count["lines"]}
    assert D(lines["SUC-T-CNT1"]["difference"]) == D("-2")
    assert D(lines["SUC-T-CNT1"]["shortage_value"]) == D("15.00")  # 2 × 7,50
    assert D(lines["SUC-T-CNT2"]["difference"]) == D("1")
    assert count["surplus_lines"] == 1
    assert session.get(StockBalance, (lot_by_no(session, "SUC-T-CNT1").id, ana.id)).qty == D("8")
    assert session.get(StockBalance, (lot_by_no(session, "SUC-T-CNT2").id, ana.id)).qty == D(
        "10"
    )  # fazla eklenmez
    assert [r for r in check_invariants(session) if not r.ok] == []


def test_seller_can_count_only_own_van(client, session):
    seller = auth_header(client, "satis1", "satis123")
    body = {
        "warehouse_id": by_code(session, Warehouse, "ANA").id,
        "lines": [{"lot_no": "ET-2026-001", "counted_qty": "1"}],
    }
    assert client.post(f"{API}/stock-counts", json=body, headers=seller).status_code == 403


def test_count_rejects_fractional_pieces(client, admin, session):
    make_lot(session, "SUC-T-CNT3", qty="10")
    body = {
        "warehouse_id": by_code(session, Warehouse, "ANA").id,
        "lines": [{"lot_no": "SUC-T-CNT3", "counted_qty": "2.5"}],
    }
    assert client.post(f"{API}/stock-counts", json=body, headers=admin).status_code == 422


# --- Ana sayfa ---


def test_dashboard_lists_expiring_low_stock_and_recalls(client, admin, session):
    make_lot(session, "SUC-T-SOON", qty="5", value="37.50", days_left=1)
    make_lot(session, "SUC-T-GONE", qty="5", value="37.50", days_left=-1)
    product = by_code(session, Product, "NARIN-SUCUK")
    product.min_stock = D("1000")
    session.flush()
    client.post(f"{API}/recalls", json={"lot_no": "ET-2026-001", "reason": "Deneme"}, headers=admin)

    data = client.get(f"{API}/dashboard", headers=admin).json()
    expiring = {row["lot_no"]: row["days_left"] for row in data["expiring"]}
    assert expiring["SUC-T-SOON"] == 1
    assert expiring["SUC-T-GONE"] == -1
    low = {row["product_code"]: D(row["qty"]) for row in data["low_stock"]}
    assert low["NARIN-SUCUK"] == D("5")  # süresi geçmiş parti satılabilir stoka sayılmaz
    assert [r["lot_no"] for r in data["open_recalls"]] == ["ET-2026-001"]
    assert D(data["stock_value"]) > 0
