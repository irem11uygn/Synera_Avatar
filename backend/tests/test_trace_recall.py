"""Görev 3 — izleme, geri çağırma, ikinci kademe (AT-06…AT-10, AT-12; FR-304…FR-310)."""

import csv
import io
from decimal import Decimal as D

import pytest
from sqlalchemy import select

from app.demo import build_demo_scenario
from app.models import Alert, Lot, Partner, Product, SaleLine, StockBalance, Warehouse
from app.models.enums import AlertKind, LotOrigin, LotStatus
from app.services.integrity import check_invariants
from tests.helpers import auth_header, by_code, lot_by_no

API = "/api/v1"


@pytest.fixture
def admin(client):
    return auth_header(client, "yonetici", "yonetici123")


@pytest.fixture
def demo(session):
    """Şartname senaryosu: URT-2026-045 → SUC-2026-045 → Market A 30 / B 25 / C 30 (+ parçalama)."""
    build_demo_scenario(session)
    session.flush()


def part_lot(session, product_code: str) -> Lot:
    return session.scalars(
        select(Lot)
        .join(Product, Product.id == Lot.product_id)
        .where(Product.code == product_code, Lot.origin == LotOrigin.PARCALAMA)
    ).one()


def recall(client, admin, lot_no="ET-2026-001", reason="Tedarikçi laboratuvar sonucu: uygunsuz") -> dict:
    response = client.post(f"{API}/recalls", json={"lot_no": lot_no, "reason": reason}, headers=admin)
    assert response.status_code == 201, response.text
    return response.json()


def by_customer(recipients: list[dict]) -> dict[str, dict]:
    return {r["customer"]: r for r in recipients}


def test_demo_scenario_is_consistent(session, demo):
    """FR-309: senaryo kurulumdan sonra hazır; defter ve özetler tutarlı."""
    sucuk = lot_by_no(session, "SUC-2026-045")
    assert (sucuk.initial_qty, sucuk.remaining_qty, sucuk.initial_value) == (D(85), D(0), D("1543.50"))
    assert [r.code for r in check_invariants(session) if not r.ok] == []


def test_at06_forward_trace_finds_markets(client, admin, demo):
    body = client.get(f"{API}/trace/forward/ET-2026-001", headers=admin).json()

    assert [(lot["lot_no"], lot["depth"]) for lot in body["lots"]] == [
        ("ET-2026-001", 0),
        ("SUC-2026-045", 1),
    ]
    assert [(k["parent_lot_no"], k["child_lot_no"], D(k["qty"]), k["doc_no"]) for k in body["links"]] == [
        ("ET-2026-001", "SUC-2026-045", D(100), "URT-2026-045")
    ]
    assert body["stock"] == []  # 85 paketin hepsi satıldı
    markets = by_customer(body["recipients"])
    assert {name: D(r["qty"]) for name, r in markets.items()} == {
        "Market A": D(30),
        "Market B": D(25),
        "Market C": D(30),
    }
    assert [s["sale_no"] for s in markets["Market A"]["sales"]] == ["SAT-2026-0101"]
    assert markets["Market A"]["contact"]["phone"] and markets["Market A"]["contact"]["person"]
    assert markets["Market A"]["sales"][0]["channel"] == "ANDROID"


def test_at09_onward_delivery_is_certain_only_when_recorded(client, admin, demo):
    markets = by_customer(client.get(f"{API}/trace/forward/ET-2026-001", headers=admin).json()["recipients"])

    b = markets["Market B"]
    assert b["onward_status"] == "KAYITLI" and D(b["onward_unknown_qty"]) == 0
    assert [(i["recipient"], D(i["qty"])) for i in b["onward_items"]] == [
        ("Market B Şube 1", D(15)),
        ("Market B Şube 2", D(10)),
    ]
    a = markets["Market A"]
    assert (a["onward_status"], a["onward_items"], D(a["onward_unknown_qty"])) == ("BILINMIYOR", [], D(30))


def test_at07_backward_trace_finds_raw_materials_and_suppliers(client, admin, demo):
    body = client.get(f"{API}/trace/backward/SUC-2026-045", headers=admin).json()

    assert body["source"]["lot_no"] == "SUC-2026-045"
    assert sorted(lot["lot_no"] for lot in body["lots"] if lot["depth"] == 1) == [
        "BAG-2026-007",
        "BAH-2026-014",
        "ET-2026-001",
    ]
    suppliers = {s["lot_no"]: (s["supplier"], s["purchase_doc_no"]) for s in body["suppliers"]}
    assert suppliers["ET-2026-001"] == ("Örnek Et Tedarik", "FAT-ET-2026-0412")
    assert len(suppliers) == 3
    [process] = body["processes"]
    assert (process["process"], process["doc_no"], process["output_lots"]) == (
        "URETIM",
        "URT-2026-045",
        ["SUC-2026-045"],
    )
    assert sorted(process["input_lots"]) == ["BAG-2026-007", "BAH-2026-014", "ET-2026-001"]


def test_unknown_lot_is_404(client, admin):
    response = client.get(f"{API}/trace/forward/YOK-1", headers=admin)
    assert response.status_code == 404 and response.json()["error"]["code"] == "NOT_FOUND"


def test_at08_recall_blocks_source_and_descendants_and_lists_markets(client, admin, session, demo):
    body = recall(client, admin)

    assert body["recall_no"] == "GC-2026-001" and body["status"] == "ACIK"
    assert {lot["lot_no"]: lot["status"] for lot in body["lots"]} == {
        "ET-2026-001": "BLOKE",
        "SUC-2026-045": "BLOKE",
    }
    assert lot_by_no(session, "SUC-2026-045").status == LotStatus.BLOKE
    assert lot_by_no(session, "BAH-2026-014").status == LotStatus.AKTIF  # kardeş girdi etkilenmez
    assert (body["lot_count"], body["customer_count"], body["violation_count"]) == (2, 3, 0)
    assert {unit: D(qty) for unit, qty in body["held_by_customers"].items()} == {"ADET": D(85)}
    assert body["started_by_name"]

    again = client.post(f"{API}/recalls", json={"lot_no": "ET-2026-001", "reason": "x"}, headers=admin)
    assert again.status_code == 409 and again.json()["error"]["code"] == "INVALID_STATE"


def test_at08_contact_list_downloads_as_csv(client, admin, demo):
    started = recall(client, admin)
    response = client.get(f"{API}/recalls/{started['id']}/export.csv", headers=admin)

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/csv")
    assert "GC-2026-001" in response.headers["content-disposition"]
    text = response.content.decode("utf-8-sig")
    rows = list(csv.reader(io.StringIO(text), delimiter=";"))
    assert rows[0][:3] == ["Geri çağırma", "Kademe", "Alıcı"]
    people = [(row[2], row[9]) for row in rows[1:]]
    assert ("Market A", "30") in people and ("Market C", "30") in people
    assert ("Market B Şube 1", "15") in people and ("Market B Şube 2", "10") in people
    a_row = next(row for row in rows[1:] if row[2] == "Market A")
    assert a_row[12] == "Bilinen son alıcı; sonrası bilinmiyor"


def test_recall_requires_reason_and_existing_lot(client, admin):
    assert (
        client.post(f"{API}/recalls", json={"lot_no": "ET-2026-001", "reason": ""}, headers=admin).status_code
        == 422
    )
    missing = client.post(f"{API}/recalls", json={"lot_no": "YOK-1", "reason": "x"}, headers=admin)
    assert missing.status_code == 404


def test_at10_blocked_lot_is_returned_destroyed_and_books_stay_consistent(client, admin, session, demo):
    started = recall(client, admin)
    markets = by_customer(client.get(f"{API}/recalls/{started['id']}", headers=admin).json()["recipients"])
    line_a = markets["Market A"]["sales"][0]["sale_line_id"]

    returned = client.post(
        f"{API}/returns", json={"sale_line_id": line_a, "qty": "30", "reason": "Geri çağırma"}, headers=admin
    )
    assert returned.status_code == 201, returned.text  # bloke lota iade alınır (geri toplama)
    main = by_code(session, Warehouse, "ANA")
    assert session.get(StockBalance, (lot_by_no(session, "SUC-2026-045").id, main.id)).qty == D(30)

    van = by_code(session, Warehouse, "ARAC-01")
    moved = client.post(
        f"{API}/transfers",
        json={
            "from_warehouse_id": main.id,
            "to_warehouse_id": van.id,
            "lines": [{"lot_no": "SUC-2026-045", "qty": "1"}],
        },
        headers=admin,
    )
    assert moved.status_code == 409 and moved.json()["error"]["code"] == "LOT_BLOCKED"

    after_return = by_customer(
        client.get(f"{API}/recalls/{started['id']}", headers=admin).json()["recipients"]
    )
    assert (D(after_return["Market A"]["qty"]), D(after_return["Market A"]["returned_qty"])) == (D(0), D(30))

    closed = client.post(
        f"{API}/recalls/{started['id']}/close",
        json={"resolution": "IMHA", "note": "İade edilen mal imha edildi"},
        headers=admin,
    )
    assert closed.status_code == 200, closed.text
    assert (closed.json()["status"], closed.json()["resolution"], closed.json()["stock"]) == (
        "KAPANDI",
        "IMHA",
        [],
    )
    assert lot_by_no(session, "SUC-2026-045").status == LotStatus.BLOKE
    assert [r.code for r in check_invariants(session) if not r.ok] == []

    twice = client.post(f"{API}/recalls/{started['id']}/close", json={"resolution": "IMHA"}, headers=admin)
    assert twice.status_code == 409


def test_recall_released_unblocks_lots(client, admin, session, demo):
    started = recall(client, admin)
    response = client.post(
        f"{API}/recalls/{started['id']}/close", json={"resolution": "SERBEST"}, headers=admin
    )
    assert response.status_code == 200
    assert lot_by_no(session, "ET-2026-001").status == LotStatus.AKTIF
    assert lot_by_no(session, "SUC-2026-045").status == LotStatus.AKTIF


def test_at12_offline_sale_after_recall_is_flagged_in_the_list(client, admin, session, demo):
    """Parça lotları araçta; kuzu geri çağrılır, cihaz eşitlemeden satar → listede ihlal + uyarı."""
    but = part_lot(session, "KUZU-BUT")
    started = recall(client, admin, lot_no="KUZU-2026-012", reason="Veteriner raporu")
    assert {lot["lot_no"] for lot in started["lots"]} >= {"KUZU-2026-012", but.lot_no}

    seller = auth_header(client, "satis1", "satis123")
    pulled = client.get(f"{API}/sync/pull", params={"since": 0}, headers=seller).json()
    assert {lot["lot_no"]: lot["status"] for lot in pulled["lots"]}[but.lot_no] == "BLOKE"

    sale = {
        "client_uuid": "7d0c2b8e-3f43-4a35-9c55-1c2a3b4d5e6f",
        "customer_id": by_code(session, Partner, "M-C").id,
        "warehouse_id": by_code(session, Warehouse, "ARAC-01").id,
        "sold_at": "2026-10-27T10:12:00+03:00",
        "lines": [{"lot_no": but.lot_no, "qty": "2", "unit_price": "22.00"}],
    }
    [result] = client.post(
        f"{API}/sync/push", json={"device_id": "t", "sales": [sale]}, headers=seller
    ).json()["results"]
    assert result["status"] == "ACCEPTED_WITH_WARNING"

    body = client.get(f"{API}/recalls/{started['id']}", headers=admin).json()
    flagged = [r for r in body["recipients"] if r["recall_violation"]]
    assert [(r["customer"], r["lot_no"], D(r["qty"])) for r in flagged] == [("Market C", but.lot_no, D(2))]
    assert body["violation_count"] == 1

    # Geri çağırma başlatılınca da alarm açılır (GERI_CAGIRMA, bloke lotta stok); ihlal ayrı, kritik.
    alerts = client.get(f"{API}/alerts", params={"only_open": True}, headers=admin).json()
    violations = [a for a in alerts if a["kind"] == "GERI_CAGIRMA_IHLALI"]
    assert len(violations) == 1 and but.lot_no in violations[0]["message"]
    assert violations[0]["severity"] == "KRITIK"
    assert {a["kind"] for a in alerts} >= {"GERI_CAGIRMA", "BLOKE_STOK"}
    acked = client.post(f"{API}/alerts/{violations[0]['id']}/ack", headers=admin).json()
    assert acked["acknowledged_at"] is not None and acked["acknowledged_by_name"]
    still_open = client.get(f"{API}/alerts", params={"only_open": True}, headers=admin).json()
    assert violations[0]["id"] not in {a["id"] for a in still_open}
    violation = session.scalars(select(Alert).where(Alert.kind == AlertKind.GERI_CAGIRMA_IHLALI)).one()
    assert violation.acknowledged_at is not None


def test_returns_value_back_exactly_what_left(client, admin, session, demo):
    """Kısmi iadeler kuruşu kuruşuna: satırın tamamı dönünce lota dönen değer = satıştaki maliyet."""
    markets = by_customer(client.get(f"{API}/trace/forward/ET-2026-001", headers=admin).json()["recipients"])
    line_c = markets["Market C"]["sales"][0]["sale_line_id"]
    sucuk = lot_by_no(session, "SUC-2026-045")

    for qty in ("7", "13", "10"):
        response = client.post(f"{API}/returns", json={"sale_line_id": line_c, "qty": qty}, headers=admin)
        assert response.status_code == 201, response.text
    session.refresh(sucuk)
    assert sucuk.remaining_qty == D(30)
    # C son satıştı; ortalama maliyetle kalan kuruşları almıştı: 1.543,50 − 544,76 (A) − 453,97 (B)
    assert sucuk.remaining_value == session.get(SaleLine, line_c).cost_amount == D("544.77")

    over = client.post(f"{API}/returns", json={"sale_line_id": line_c, "qty": "1"}, headers=admin)
    assert over.status_code == 422
    assert [r.code for r in check_invariants(session) if not r.ok] == []
    assert len(client.get(f"{API}/returns", headers=admin).json()) == 3


def test_onward_deliveries_cannot_exceed_what_the_customer_holds(client, admin, session, demo):
    markets = by_customer(client.get(f"{API}/trace/forward/ET-2026-001", headers=admin).json()["recipients"])
    line_a = markets["Market A"]["sales"][0]["sale_line_id"]
    url = f"{API}/sale-lines/{line_a}/onward-deliveries"
    branch = by_code(session, Partner, "M-B-S1").id

    ok = client.post(url, json={"recipient_partner_id": branch, "qty": "20"}, headers=admin)
    assert ok.status_code == 201, ok.text
    too_much = client.post(url, json={"recipient_partner_id": branch, "qty": "11"}, headers=admin)
    assert too_much.status_code == 422
    assert [d["qty"] for d in client.get(url, headers=admin).json()] == ["20.000"]

    a = by_customer(client.get(f"{API}/trace/forward/ET-2026-001", headers=admin).json()["recipients"])[
        "Market A"
    ]
    assert (a["onward_status"], D(a["onward_unknown_qty"])) == ("KISMEN", D(10))


def test_waste_and_reversal_never_rewrite_the_ledger(client, admin, session, demo):
    omuz = part_lot(session, "KUZU-OMUZ")
    main = by_code(session, Warehouse, "ANA")
    fire = client.post(
        f"{API}/adjustments",
        json={
            "lot_no": omuz.lot_no,
            "warehouse_id": main.id,
            "qty": "1.250",
            "reason": "Soğuk zincir kırıldı",
        },
        headers=admin,
    )
    assert fire.status_code == 201, fire.text
    session.refresh(omuz)
    assert omuz.remaining_qty == D("3.750")

    movements = client.get(f"{API}/lots/{omuz.lot_no}/movements", headers=admin).json()
    fire_movement = next(m for m in movements if m["type"] == "FIRE")
    reversed_ = client.post(
        f"{API}/movements/{fire_movement['id']}/reverse",
        json={"reason": "Yanlış lot seçilmiş"},
        headers=admin,
    )
    assert reversed_.status_code == 201, reversed_.text
    assert [(m["type"], D(m["qty"])) for m in reversed_.json()] == [("TERS_KAYIT", D("1.250"))]
    session.refresh(omuz)
    assert omuz.remaining_qty == D(5)
    assert len(client.get(f"{API}/lots/{omuz.lot_no}/movements", headers=admin).json()) == len(movements) + 1

    twice = client.post(f"{API}/movements/{fire_movement['id']}/reverse", json={"reason": "x"}, headers=admin)
    assert twice.status_code == 422
    production = next(m for m in movements if m["type"] == "PARCALAMA_GIRIS")
    refused = client.post(f"{API}/movements/{production['id']}/reverse", json={"reason": "x"}, headers=admin)
    assert refused.status_code == 409 and refused.json()["error"]["code"] == "INVALID_STATE"
    assert [r.code for r in check_invariants(session) if not r.ok] == []


def test_manual_transfer_is_reversed_as_a_pair(client, admin, session, demo):
    main, van = by_code(session, Warehouse, "ANA"), by_code(session, Warehouse, "ARAC-01")
    omuz = part_lot(session, "KUZU-OMUZ")
    moved = client.post(
        f"{API}/transfers",
        json={
            "from_warehouse_id": main.id,
            "to_warehouse_id": van.id,
            "lines": [{"lot_no": omuz.lot_no, "qty": "2"}],
        },
        headers=admin,
    )
    assert moved.status_code == 201
    out = next(
        m
        for m in client.get(f"{API}/lots/{omuz.lot_no}/movements", headers=admin).json()
        if m["type"] == "TRANSFER_CIKIS"
    )
    response = client.post(
        f"{API}/movements/{out['id']}/reverse", json={"reason": "Yanlış araç"}, headers=admin
    )
    assert response.status_code == 201, response.text
    assert [(m["warehouse_code"], D(m["qty"])) for m in response.json()] == [
        ("ARAC-01", D(-2)),
        ("ANA", D(2)),
    ]
    assert session.get(StockBalance, (omuz.id, van.id)).qty == 0
    assert [r.code for r in check_invariants(session) if not r.ok] == []


def test_sales_user_cannot_trace_or_recall(client):
    seller = auth_header(client, "satis1", "satis123")
    assert client.get(f"{API}/trace/forward/ET-2026-001", headers=seller).status_code == 403
    assert (
        client.post(
            f"{API}/recalls", json={"lot_no": "ET-2026-001", "reason": "x"}, headers=seller
        ).status_code
        == 403
    )
