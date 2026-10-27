"""Yeniden işleme (FR-302, FR-303): iade gelen sucuğun yeniden paketlenmesi, izleme ve bütünlük."""

from decimal import Decimal as D

import pytest

from app.demo import build_demo_scenario
from app.models import Product
from app.services.integrity import check_invariants
from tests.helpers import auth_header, by_code, lot_by_no

API = "/api/v1"


@pytest.fixture
def admin(client):
    return auth_header(client, "yonetici", "yonetici123")


@pytest.fixture
def returned(client, admin, session):
    """Demo senaryosu + Market A'dan 30 paket iade (ana depoda SUC-2026-045 30 paket)."""
    build_demo_scenario(session)
    session.flush()
    trace = client.get(f"{API}/trace/forward/ET-2026-001", headers=admin).json()
    line_a = next(r for r in trace["recipients"] if r["customer"] == "Market A")["sales"][0]["sale_line_id"]
    response = client.post(f"{API}/returns", json={"sale_line_id": line_a, "qty": "30"}, headers=admin)
    assert response.status_code == 201, response.text


def body(session, qty="10", extra="5.00", lot_no="SUC-2026-045") -> dict:
    return {
        "inputs": [{"lot_no": lot_no, "qty": qty}],
        "output_product_id": by_code(session, Product, "NARIN-SUCUK").id,
        "output_qty": qty,
        "extra_cost": extra,
        "note": "İade gelen paketler yeniden etiketlendi",
    }


def test_reprocessing_creates_a_linked_lot_valued_from_its_inputs(client, admin, session, returned):
    response = client.post(f"{API}/reprocessing", json=body(session), headers=admin)
    assert response.status_code == 201, response.text
    data = response.json()
    assert (data["order_no"], data["output_lot_no"]) == ("YIS-2026-001", "SUC-YIS-2026-001")
    [item] = data["inputs"]
    assert D(data["total_value"]) == D(item["value"]) + D("5.00")
    assert lot_by_no(session, "SUC-YIS-2026-001").origin == "YENIDEN_ISLEME"

    trace = client.get(f"{API}/trace/forward/ET-2026-001", headers=admin).json()
    assert ("SUC-YIS-2026-001", 2) in [(lot["lot_no"], lot["depth"]) for lot in trace["lots"]]
    link = next(k for k in trace["links"] if k["child_lot_no"] == "SUC-YIS-2026-001")
    assert (link["process"], link["doc_no"], D(link["qty"])) == ("YENIDEN_ISLEME", "YIS-2026-001", D(10))
    assert [r.code for r in check_invariants(session) if not r.ok] == []
    assert [r["order_no"] for r in client.get(f"{API}/reprocessing", headers=admin).json()] == [
        "YIS-2026-001"
    ]


def test_reprocessing_is_not_listed_as_external_production(client, admin, session, returned):
    data = client.post(f"{API}/reprocessing", json=body(session), headers=admin).json()
    assert [o["order_no"] for o in client.get(f"{API}/production-orders", headers=admin).json()] == [
        "URT-2026-045"
    ]
    assert client.get(f"{API}/production-orders/{data['id']}", headers=admin).status_code == 404


def test_blocked_lot_cannot_be_reprocessed(client, admin, session, returned):
    client.post(f"{API}/recalls", json={"lot_no": "ET-2026-001", "reason": "Laboratuvar"}, headers=admin)
    response = client.post(f"{API}/reprocessing", json=body(session), headers=admin)
    assert response.status_code == 409 and response.json()["error"]["code"] == "LOT_BLOCKED"


def test_reprocessing_needs_stock_and_whole_packages(client, admin, session, returned):
    too_much = client.post(f"{API}/reprocessing", json=body(session, qty="31"), headers=admin)
    assert too_much.status_code == 409 and too_much.json()["error"]["code"] == "INSUFFICIENT_STOCK"
    half = body(session)
    half["output_qty"] = "9.5"
    assert client.post(f"{API}/reprocessing", json=half, headers=admin).status_code == 422
