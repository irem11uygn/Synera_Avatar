"""Görev 1 — dış hizmetle üretim API'si (AT-01, AT-02, AT-15; FR-105…FR-111)."""

from datetime import timedelta
from decimal import Decimal as D

import pytest

from app.domain.clock import business_today
from app.models import Lot, Partner, Product
from app.models.enums import LotStatus
from app.services.integrity import check_invariants
from app.services.lot_graph import descendants
from tests.helpers import auth_header, by_code, lot_by_no

URL = "/api/v1/production-orders"
SCENARIO_INPUTS = [
    {"lot_no": "ET-2026-001", "qty": "100"},
    {"lot_no": "BAH-2026-014", "qty": "2"},
    {"lot_no": "BAG-2026-007", "qty": "5"},
]


@pytest.fixture
def admin(client):
    return auth_header(client, "yonetici", "yonetici123")


def new_order(
    client,
    admin,
    session,
    *,
    planned="85",
    inputs=SCENARIO_INPUTS,
    subcontractor="FSN-01",
    product="NARIN-SUCUK",
):
    body = {
        "subcontractor_id": by_code(session, Partner, subcontractor).id,
        "output_product_id": by_code(session, Product, product).id,
        "planned_qty": planned,
        "service_unit_price": "5.50",
        "inputs": inputs,
    }
    return client.post(URL, json=body, headers=admin)


def created(client, admin, session, **kwargs) -> dict:
    response = new_order(client, admin, session, **kwargs)
    assert response.status_code == 201, response.text
    return response.json()


def ship(client, admin, order) -> dict:
    response = client.post(f"{URL}/{order['id']}/ship", headers=admin)
    assert response.status_code == 200, response.text
    return response.json()


def complete(client, admin, order, *, received="85", inputs=None, **extra):
    inputs = inputs or [{"lot_no": i["lot_no"], "consumed_qty": i["qty"]} for i in SCENARIO_INPUTS]
    body = {"received_qty": received, "inputs": inputs, "service_invoice_no": "FSN-2026-310", **extra}
    return client.post(f"{URL}/{order['id']}/complete", json=body, headers=admin)


def balances(client, admin, lot_no) -> dict[str, D]:
    lot = client.get(f"/api/v1/lots/{lot_no}", headers=admin).json()
    return {b["warehouse_code"]: D(b["qty"]) for b in lot["balances"]}


def test_at01_narin_sucuk_end_to_end(client, admin, session):
    order = created(client, admin, session)
    assert (order["order_no"], order["status"]) == ("URT-2026-045", "TASLAK")

    shipped = ship(client, admin, order)
    assert shipped["status"] == "SEVK_EDILDI"
    assert {k: v for k, v in balances(client, admin, "ET-2026-001").items() if v} == {
        "DIS-FSN-01": D("100")
    }  # mal hâlâ bizim, fasoncuda

    response = complete(client, admin, order)
    assert response.status_code == 200, response.text
    body = response.json()
    assert (body["status"], body["output_lot_no"]) == ("TAMAMLANDI", "SUC-2026-045")
    cost = {key: D(value) for key, value in body["cost"].items()}
    assert cost == {
        "raw_materials": D("1076.00"),
        "service": D("467.50"),
        "total": D("1543.50"),
        "ekp": D("18.158824"),
        "ekp_display": D("18.16"),
    }
    assert {k: D(v) for k, v in body["sales"].items()} == {
        "vkp": D("24.90"),
        "gross_profit_per_unit": D("6.74"),
        "margin_pct": D("27.07"),
    }
    assert D(body["yield"]["yield_main_pct"]) == D("85.00")  # 85 kg sucuk / 100 kg et
    assert D(body["yield"]["yield_total_pct"]) == D("79.44")  # 85 / 107
    assert [D(i["consumed_value"]) for i in body["inputs"]] == [D("970.00"), D("48.00"), D("58.00")]


def test_at01_output_lot_is_linked_valued_and_traceable(client, admin, session):
    order = created(client, admin, session)
    ship(client, admin, order)
    complete(client, admin, order)

    lot = client.get("/api/v1/lots/SUC-2026-045", headers=admin).json()
    assert (D(lot["remaining_qty"]), D(lot["remaining_value"]), lot["origin"]) == (
        D("85"),
        D("1543.50"),
        "URETIM",
    )
    assert [(p["lot_no"], D(p["qty"])) for p in lot["parents"]] == [
        ("ET-2026-001", D("100")),
        ("BAH-2026-014", D("2")),
        ("BAG-2026-007", D("5")),
    ]
    assert lot["expiry_date"] == (business_today() + timedelta(days=60)).isoformat()  # işletmenin yerel günü
    sucuk = lot_by_no(session, "SUC-2026-045")
    assert sucuk.id in descendants(session, lot_by_no(session, "ET-2026-001").id)
    assert [(r.code, r.violations) for r in check_invariants(session) if not r.ok] == []


def test_at15_quantity_differences_and_returned_spice(client, admin, session):
    """Planlanan 87, teslim 85; 0,5 kg baharat iade. EKP teslim alınan 85'e göre."""
    order = created(client, admin, session, planned="87")
    ship(client, admin, order)
    inputs = [
        {"lot_no": "ET-2026-001", "consumed_qty": "100"},
        {"lot_no": "BAH-2026-014", "consumed_qty": "1.5", "returned_qty": "0.5"},
        {"lot_no": "BAG-2026-007", "consumed_qty": "5"},
    ]
    response = complete(client, admin, order, inputs=inputs)
    assert response.status_code == 200, response.text
    body = response.json()
    assert D(body["quantity_difference"]) == D("-2")
    assert D(body["cost"]["raw_materials"]) == D("1064.00")  # 970 + 36 + 58
    assert D(body["cost"]["total"]) == D("1531.50")
    assert D(body["cost"]["ekp_display"]) == D("18.02")
    spice = next(i for i in body["inputs"] if i["lot_no"] == "BAH-2026-014")
    assert (D(spice["shipped_qty"]), D(spice["consumed_qty"]), D(spice["returned_qty"])) == (
        D("2"),
        D("1.5"),
        D("0.5"),
    )
    assert balances(client, admin, "BAH-2026-014") == {"ANA": D("0.5")}
    assert lot_by_no(session, "BAH-2026-014").remaining_value == D("12.00")


def test_service_invoice_different_from_suggestion_needs_note(client, admin, session):
    order = created(client, admin, session)
    ship(client, admin, order)
    response = complete(client, admin, order, service_amount="480.00")
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "AMOUNT_MISMATCH_NOTE_REQUIRED"
    assert response.json()["error"]["details"] == {"suggested_amount": "467.50", "invoice_amount": "480.00"}

    response = complete(
        client, admin, order, service_amount="480.00", service_note="Nakliye faturaya eklendi"
    )
    assert response.status_code == 200, response.text
    assert D(response.json()["cost"]["total"]) == D("1556.00")


def test_failed_completion_leaves_nothing_behind(client, admin, session):
    """Hatalı kabul isteği hiçbir hareket veya lot bırakmaz (NFR-003)."""
    order = created(client, admin, session)
    ship(client, admin, order)
    bad = [{"lot_no": i["lot_no"], "consumed_qty": i["qty"]} for i in SCENARIO_INPUTS]
    bad[0]["consumed_qty"] = "99"  # 99 + 0 ≠ 100
    response = complete(client, admin, order, inputs=bad)
    assert response.status_code == 422
    assert "sevk edilen miktara" in response.json()["error"]["message"]
    assert session.query(Lot).filter(Lot.lot_no == "SUC-2026-045").count() == 0
    assert client.get(f"{URL}/{order['id']}", headers=admin).json()["status"] == "SEVK_EDILDI"


def test_status_flow_is_enforced(client, admin, session):
    order = created(client, admin, session)
    assert complete(client, admin, order).json()["error"]["code"] == "INVALID_STATE"
    ship(client, admin, order)
    second_ship = client.post(f"{URL}/{order['id']}/ship", headers=admin)
    assert (second_ship.status_code, second_ship.json()["error"]["code"]) == (409, "INVALID_STATE")
    cancel = client.post(f"{URL}/{order['id']}/cancel", headers=admin)
    assert (cancel.status_code, cancel.json()["error"]["code"]) == (422, "VALIDATION_ERROR")  # neden zorunlu
    assert complete(client, admin, order).status_code == 200
    cancel = client.post(f"{URL}/{order['id']}/cancel", headers=admin, json={"note": "deneme"})
    assert (cancel.status_code, cancel.json()["error"]["code"]) == (409, "INVALID_STATE")


def test_shipped_order_cancel_returns_materials(client, admin, session):
    """Fasoncu üretmediyse sevk edilen hammadde iade transferiyle ana depoya döner, emir iptal olur."""
    order = created(client, admin, session)
    ship(client, admin, order)
    assert {k: v for k, v in balances(client, admin, "ET-2026-001").items() if v} == {"DIS-FSN-01": D("100")}
    response = client.post(f"{URL}/{order['id']}/cancel", headers=admin, json={"note": "Fasoncu üretemedi"})
    assert response.status_code == 200, response.text
    assert response.json()["status"] == "IPTAL"
    assert {k: v for k, v in balances(client, admin, "ET-2026-001").items() if v} == {"ANA": D("100")}


def test_draft_order_can_be_cancelled(client, admin, session):
    order = created(client, admin, session)
    assert client.post(f"{URL}/{order['id']}/cancel", headers=admin).json()["status"] == "IPTAL"


def test_shipping_more_than_stock_is_rejected_atomically(client, admin, session):
    order = created(client, admin, session, inputs=[{"lot_no": "ET-2026-001", "qty": "150"}])
    response = client.post(f"{URL}/{order['id']}/ship", headers=admin)
    assert (response.status_code, response.json()["error"]["code"]) == (409, "INSUFFICIENT_STOCK")
    assert balances(client, admin, "ET-2026-001") == {"ANA": D("100")}
    assert client.get(f"{URL}/{order['id']}", headers=admin).json()["status"] == "TASLAK"


def test_blocked_lot_cannot_be_planned(client, admin, session):
    lot_by_no(session, "ET-2026-001").status = LotStatus.BLOKE
    session.flush()
    response = new_order(client, admin, session)
    assert (response.status_code, response.json()["error"]["code"]) == (409, "LOT_BLOCKED")


def test_packages_must_be_whole_numbers(client, admin, session):
    order = created(client, admin, session)
    ship(client, admin, order)
    response = complete(client, admin, order, received="84.5")
    assert response.status_code == 422
    assert "tam sayı" in response.json()["error"]["message"]


def test_order_requires_subcontractor_and_finished_product(client, admin, session):
    assert new_order(client, admin, session, subcontractor="M-A").status_code == 422
    assert new_order(client, admin, session, product="ET").status_code == 422


def test_sales_user_cannot_manage_production(client):
    headers = auth_header(client, "satis1", "satis123")
    assert client.get(URL, headers=headers).status_code == 403
