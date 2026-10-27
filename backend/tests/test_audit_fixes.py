"""27 Ekim denetiminde bulunan hataların düzeltmeleri (DENETIM_RAPORU_27Ekim)."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.exc import IntegrityError

from app.api.csv_export import _safe_text
from app.main import create_app
from app.models import Partner, Product
from tests.helpers import auth_header, by_code, make_lot, store_sale

API = "/api/v1"


@pytest.fixture
def admin(client):
    return auth_header(client, "yonetici", "yonetici123")


def purchase(session, doc_no, lot_no):
    return {
        "supplier_id": by_code(session, Partner, "TED-ET").id,
        "doc_no": doc_no,
        "doc_date": "2026-10-25",
        "lines": [
            {
                "product_id": by_code(session, Product, "ET").id,
                "lot_no": lot_no,
                "qty": "10",
                "unit_price": "9.70",
            }
        ],
    }


def test_same_supplier_invoice_cannot_be_entered_twice(client, admin, session):
    assert (
        client.post(f"{API}/purchases", json=purchase(session, "FAT-9", "ET-T-A"), headers=admin).status_code
        == 201
    )
    again = client.post(f"{API}/purchases", json=purchase(session, " FAT-9 ", "ET-T-B"), headers=admin)
    assert again.status_code == 422
    assert "FAT-9" in again.json()["error"]["message"]


def test_unknown_warehouse_is_404_not_database_error(client, admin):
    body = {"lot_no": "ET-2026-001", "warehouse_id": 999999, "qty": "1", "reason": "Deneme"}
    response = client.post(f"{API}/adjustments", json=body, headers=admin)
    assert (response.status_code, response.json()["error"]["code"]) == (404, "NOT_FOUND")


def test_unit_of_product_with_lots_cannot_change(client, admin, session):
    product = by_code(session, Product, "ET")
    body = {
        "code": "ET",
        "name": product.name,
        "kind": "HAMMADDE",
        "base_unit": "ADET",
        "unit_weight_kg": "1",
    }
    response = client.put(f"{API}/products/{product.id}", json=body, headers=admin)
    assert response.status_code == 422
    assert (
        "lot" in response.json()["error"]["message"].lower() or "parti" in response.json()["error"]["message"]
    )


def test_branch_cycle_is_rejected(client, admin, session):
    parent = by_code(session, Partner, "M-B")
    branch = by_code(session, Partner, "M-B-S1")
    body = {"code": "M-B", "name": parent.name, "is_customer": True, "parent_id": branch.id}
    response = client.put(f"{API}/partners/{parent.id}", json=body, headers=admin)
    assert response.status_code == 422
    assert "döngü" in response.json()["error"]["message"]


def test_returns_respect_customer_onward_deliveries(client, admin, session):
    """Müşterinin kendi alıcılarına dağıttığı mal iade alınamaz (izleme listesi tutarlı kalır)."""
    make_lot(session, "SUC-T-ONW", qty="20", value="150.00")
    sale = store_sale(client, admin, session, {"lot_no": "SUC-T-ONW", "qty": "10"}).json()
    line_id = sale["lines"][0]["id"]
    recipient = by_code(session, Partner, "M-B-S1").id
    onward = client.post(
        f"{API}/sale-lines/{line_id}/onward-deliveries",
        json={"recipient_partner_id": recipient, "qty": "8"},
        headers=admin,
    )
    assert onward.status_code == 201, onward.text
    too_much = client.post(f"{API}/returns", json={"sale_line_id": line_id, "qty": "5"}, headers=admin)
    assert too_much.status_code == 422
    assert (
        client.post(f"{API}/returns", json={"sale_line_id": line_id, "qty": "2"}, headers=admin).status_code
        == 201
    )


@pytest.mark.parametrize(
    ("text", "expected"),
    [("=HYPERLINK(1)", "'=HYPERLINK(1)"), ("+90 555", "'+90 555"), ("@x", "'@x"), ("Market A", "Market A")],
)
def test_csv_cells_cannot_become_formulas(text, expected):
    assert _safe_text(text) == expected


def test_database_conflict_is_409_with_turkish_message():
    app = create_app()

    @app.get("/catisma")
    def conflict() -> None:
        raise IntegrityError("INSERT ...", {}, Exception("Duplicate entry"))

    response = TestClient(app, raise_server_exceptions=False).get("/catisma")
    assert (response.status_code, response.json()["error"]["code"]) == (409, "CONFLICT")
    assert "Duplicate" not in response.json()["error"]["message"]  # iç ayrıntı istemciye sızmaz


def test_unexpected_error_is_500_without_details():
    app = create_app()

    @app.get("/bozuk")
    def broken() -> None:
        raise RuntimeError("gizli ayrıntı")

    response = TestClient(app, raise_server_exceptions=False).get("/bozuk")
    assert (response.status_code, response.json()["error"]["code"]) == (500, "INTERNAL_ERROR")
    assert "gizli" not in response.text
