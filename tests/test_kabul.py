"""Şartname kabul testleri AT-01…AT-15 (docs/testing_strategy.md §3), çalışan sisteme karşı.

Sıra önemlidir: önce yalnız okuyan ve yeni lotlarla çalışan testler, sonra demo verisini değiştirenler
(geri çağırma). Her test kendi kabul ölçütünü şartnamedeki rakamlarla denetler.
"""

import csv
import io
import uuid
from datetime import date
from decimal import Decimal as D

import pytest

from conftest import BASE, Api

TODAY = date.today().isoformat()
PARTS = {"KUZU-BUT": "7", "KUZU-SIRT": "4", "KUZU-OMUZ": "5", "KUZU-KABURGA": "3", "KUZU-KIYMA": "3"}
STATE: dict[str, object] = {}  # testler arası taşınan kimlikler (ör. AT-01'in emri)


def purchase(admin: Api, refs, *, supplier, lines, doc_no, status=201):
    body = {
        "supplier_id": refs["partner"][supplier],
        "doc_no": doc_no,
        "doc_date": TODAY,
        "lines": lines,
    }
    response = admin.post("/purchases", body)
    assert response.status == status, response.body
    return response


def line(refs, product, lot_no, qty, price, **extra):
    return {
        "product_id": refs["product"][product],
        "lot_no": lot_no,
        "qty": qty,
        "unit_price": price,
        **extra,
    }


def sucuk_order(
    admin: Api, refs, run_id, tag, *, planned="85", received="85", spice_used="2", spice_back="0"
):
    """Şartname Görev 1: alış → emir → sevk → kabul, gerçek HTTP ile; yeni lotlarla."""
    et, bah, bag = f"ET-{tag}-{run_id}", f"BAH-{tag}-{run_id}", f"BAG-{tag}-{run_id}"
    purchase(
        admin,
        refs,
        supplier="TED-ET",
        doc_no=f"KABUL-ET-{tag}-{run_id}",
        lines=[line(refs, "ET", et, "100", "9.70")],
    )
    purchase(
        admin,
        refs,
        supplier="TED-BAH",
        doc_no=f"KABUL-BAH-{tag}-{run_id}",
        lines=[line(refs, "BAHARAT", bah, "2", "24.00")],
    )
    purchase(
        admin,
        refs,
        supplier="TED-BAG",
        doc_no=f"KABUL-BAG-{tag}-{run_id}",
        lines=[line(refs, "BAGIRSAK", bag, "5", "11.60")],
    )
    order = admin.ok(
        "POST",
        "/production-orders",
        {
            "subcontractor_id": refs["partner"]["FSN-01"],
            "output_product_id": refs["product"]["NARIN-SUCUK"],
            "planned_qty": planned,
            "service_unit_price": "5.50",
            "inputs": [
                {"lot_no": et, "qty": "100"},
                {"lot_no": bah, "qty": "2"},
                {"lot_no": bag, "qty": "5"},
            ],
        },
        status=201,
    )
    admin.ok("POST", f"/production-orders/{order['id']}/ship")
    return admin.ok(
        "POST",
        f"/production-orders/{order['id']}/complete",
        {
            "received_qty": received,
            "inputs": [
                {"lot_no": et, "consumed_qty": "100", "returned_qty": "0"},
                {"lot_no": bah, "consumed_qty": spice_used, "returned_qty": spice_back},
                {"lot_no": bag, "consumed_qty": "5", "returned_qty": "0"},
            ],
        },
    )


def cutting(admin: Api, refs, lot_no, *, method=None):
    body = {"recipe_id": refs["recipe"]["KUZU-STD"], "input_lot_no": lot_no, "input_qty": "25"}
    if method:
        body["method"] = method
    return admin.ok("POST", "/cuttings", body, status=201)


def actuals(cut, fire):
    return [
        {
            "recipe_line_id": ln["recipe_line_id"],
            "actual_qty": fire if ln["line_type"] == "FIRE" else PARTS[ln["product_code"]],
        }
        for ln in cut["lines"]
    ]


def shares(body) -> dict[str, D]:
    return {ln["product_code"]: D(ln["allocated_cost"]) for ln in body["lines"] if ln["product_code"]}


def by_customer(recipients):
    return {r["customer"]: r for r in recipients}


# --- AT-14: temiz kurulum (betik sistemi sıfırdan kurar; burada sonucu denetlenir)


def test_at14_clean_install_comes_up_with_the_scenario(admin):
    assert Api().get("/health").body["database"] == "ok"
    sucuk = admin.ok("GET", "/lots/SUC-2026-045")
    assert (D(sucuk["initial_qty"]), D(sucuk["initial_value"])) == (D(85), D("1543.50"))
    assert "URT-2026-045" in [o["order_no"] for o in admin.ok("GET", "/production-orders")]


# --- Görev 1


def test_at01_external_production_cost_over_http(admin, refs, run_id):
    order = sucuk_order(admin, refs, run_id, "AT01")
    STATE["at01_order"] = order
    assert D(order["cost"]["total"]) == D("1543.50")
    assert D(order["cost"]["ekp_display"]) == D("18.16") and D(order["cost"]["ekp"]) >= D("18.1588")
    lot = admin.ok("GET", f"/lots/{order['output_lot_no']}")
    assert D(lot["initial_value"]) == D("1543.50")
    demo = next(o for o in admin.ok("GET", "/production-orders") if o["order_no"] == "URT-2026-045")
    assert (D(demo["cost"]["total"]), D(demo["cost"]["ekp_display"])) == (D("1543.50"), D("18.16"))


def test_at02_gross_profit_and_margin():
    sales = STATE["at01_order"]["sales"]
    assert (D(sales["gross_profit_per_unit"]), D(sales["margin_pct"])) == (D("6.74"), D("27.07"))


def test_at15_quantity_differences_in_order_and_report(admin, refs, run_id):
    order = sucuk_order(admin, refs, run_id, "AT15", planned="87", spice_used="1.5", spice_back="0.5")
    assert D(order["quantity_difference"]) == D(-2)
    spice = next(i for i in order["inputs"] if i["lot_no"].startswith("BAH-"))
    assert (D(spice["consumed_qty"]), D(spice["returned_qty"])) == (D("1.5"), D("0.5"))
    assert D(order["cost"]["ekp_display"]) == D("18.02")  # (970 + 36 + 58 + 467,50) / 85
    row = next(
        r for r in admin.ok("GET", "/reports/production")["rows"] if r["order_no"] == order["order_no"]
    )
    assert D(row["qty_difference"]) == D(-2) and "iade 0.5" in row["input_differences"]


# --- Görev 2


def test_at03_cost_allocation_both_methods_to_the_cent(admin, refs, run_id):
    lot = f"KUZU-AT03-{run_id}"
    extra = [{"kind": "KESIM", "amount": "40.00"}, {"kind": "NAKLIYE", "amount": "23.50"}]
    purchase(
        admin,
        refs,
        supplier="TED-KUZU",
        doc_no=f"KABUL-KUZU-AT03-{run_id}",
        lines=[line(refs, "KUZU-BUTUN", lot, "25", "11.50", extra_costs=extra)],
    )
    assert D(admin.ok("GET", f"/lots/{lot}")["initial_value"]) == D("351.00")
    cut = cutting(admin, refs, lot)
    by_qty = admin.ok(
        "POST", f"/cuttings/{cut['id']}/preview", {"method": "MIKTAR", "outputs": actuals(cut, "3")}
    )
    assert shares(by_qty) == {
        "KUZU-BUT": D("111.68"),
        "KUZU-SIRT": D("63.82"),
        "KUZU-OMUZ": D("79.77"),
        "KUZU-KABURGA": D("47.87"),
        "KUZU-KIYMA": D("47.86"),
    }
    by_value = admin.ok(
        "POST", f"/cuttings/{cut['id']}/preview", {"method": "DEGER", "outputs": actuals(cut, "3")}
    )
    assert shares(by_value) == {
        "KUZU-BUT": D("123.41"),
        "KUZU-SIRT": D("83.34"),
        "KUZU-OMUZ": D("72.12"),
        "KUZU-KABURGA": D("33.66"),
        "KUZU-KIYMA": D("38.47"),
    }
    assert sum(shares(by_qty).values()) == sum(shares(by_value).values()) == D("351.00")
    admin.ok("PUT", f"/cuttings/{cut['id']}", {"method": "DEGER", "outputs": actuals(cut, "3")})
    approved = admin.ok("POST", f"/cuttings/{cut['id']}/approve")
    assert approved["status"] == "ONAYLANDI" and sum(shares(approved).values()) == D("351.00")
    STATE["at03_parts"] = {
        ln["product_code"]: ln["output_lot_no"] for ln in approved["lines"] if ln["product_code"]
    }


def test_at04_weight_balance_blocks_approval_until_waste_is_weighed(admin, refs, run_id):
    lot = f"KUZU-AT04-{run_id}"
    purchase(
        admin,
        refs,
        supplier="TED-KUZU",
        doc_no=f"KABUL-KUZU-AT04-{run_id}",
        lines=[line(refs, "KUZU-BUTUN", lot, "25", "11.50")],
    )
    cut = cutting(admin, refs, lot)
    admin.ok("PUT", f"/cuttings/{cut['id']}", {"outputs": actuals(cut, None)})
    missing = admin.post(f"/cuttings/{cut['id']}/approve")
    assert missing.status == 422 and missing.code == "VALIDATION_ERROR"
    admin.ok("PUT", f"/cuttings/{cut['id']}", {"outputs": actuals(cut, "0")})
    imbalance = admin.post(f"/cuttings/{cut['id']}/approve")
    assert imbalance.status == 409 and imbalance.code == "WEIGHT_IMBALANCE"
    assert "3" in imbalance.body["error"]["message"]
    admin.ok("PUT", f"/cuttings/{cut['id']}", {"outputs": actuals(cut, "3")})
    assert admin.ok("POST", f"/cuttings/{cut['id']}/approve")["status"] == "ONAYLANDI"


def test_at05_invoice_mismatch_requires_an_explanation(admin, refs, run_id):
    mismatch = line(refs, "KUZU-BUTUN", f"KUZU-AT05-{run_id}", "25", "11.50", invoice_amount="351.00")
    refused = purchase(
        admin, refs, supplier="TED-KUZU", doc_no=f"KABUL-AT05-{run_id}", lines=[mismatch], status=422
    )
    assert refused.code == "AMOUNT_MISMATCH_NOTE_REQUIRED"
    mismatch["discrepancy_note"] = "Faturaya kesim ve nakliye dahil edilmiş"
    accepted = purchase(admin, refs, supplier="TED-KUZU", doc_no=f"KABUL-AT05-{run_id}", lines=[mismatch])
    assert accepted.body["lines"][0]["discrepancy_note"]


# --- Görev 3 (demo senaryosu üzerinde)


def test_at06_forward_trace_finds_the_markets_within_two_seconds(admin):
    response = admin.get("/trace/forward/ET-2026-001")
    assert response.status == 200
    assert response.seconds < 2.0, f"İzleme {response.seconds:.2f} sn sürdü (NFR-009: < 2 sn)"
    STATE["trace_seconds"] = response.seconds
    body = response.body
    assert [lot["lot_no"] for lot in body["lots"]] == ["ET-2026-001", "SUC-2026-045"]
    assert body["stock"] == []
    markets = by_customer(body["recipients"])
    assert {name: D(r["qty"]) for name, r in markets.items()} == {
        "Market A": D(30),
        "Market B": D(25),
        "Market C": D(30),
    }
    assert all(r["contact"]["phone"] and r["contact"]["person"] for r in markets.values())
    assert [s["sale_no"] for s in markets["Market A"]["sales"]] == ["SAT-2026-0101"]


def test_at07_backward_trace_finds_raw_materials_suppliers_and_order(admin):
    body = admin.ok("GET", "/trace/backward/SUC-2026-045")
    assert {s["lot_no"]: s["supplier"] for s in body["suppliers"]} == {
        "ET-2026-001": "Örnek Et Tedarik",
        "BAH-2026-014": "Örnek Baharat",
        "BAG-2026-007": "Örnek Bağırsak",
    }
    assert [p["doc_no"] for p in body["processes"]] == ["URT-2026-045"]


def test_at09_onward_delivery_is_certain_only_when_recorded(admin):
    markets = by_customer(admin.ok("GET", "/trace/forward/ET-2026-001")["recipients"])
    assert markets["Market B"]["onward_status"] == "KAYITLI"
    assert sorted((i["recipient"], D(i["qty"])) for i in markets["Market B"]["onward_items"]) == [
        ("Market B Şube 1", D(15)),
        ("Market B Şube 2", D(10)),
    ]
    assert markets["Market A"]["onward_status"] == markets["Market C"]["onward_status"] == "BILINMIYOR"


def test_at11_same_sale_sent_twice_is_recorded_once(seller, admin, refs):
    van = admin.ok("GET", f"/lots?warehouse_id={refs['warehouse']['ARAC-01']}")
    lot = next(item["lot_no"] for item in van if item["product_code"] == "KUZU-SIRT")
    sale = {
        "client_uuid": str(uuid.uuid4()),
        "customer_id": refs["partner"]["M-A"],
        "warehouse_id": refs["warehouse"]["ARAC-01"],
        "sold_at": f"{TODAY}T10:00:00+03:00",
        "lines": [{"lot_no": lot, "qty": "1", "unit_price": "26.00"}],
    }
    [first] = seller.ok("POST", "/sync/push", {"device_id": "kabul", "sales": [sale]})["results"]
    [second] = seller.ok("POST", "/sync/push", {"device_id": "kabul", "sales": [sale]})["results"]
    assert (first["status"], second["status"]) == ("ACCEPTED", "DUPLICATE")
    assert first["sale_no"] == second["sale_no"]
    assert [s["sale_no"] for s in admin.ok("GET", "/sales")].count(first["sale_no"]) == 1


def test_at08_recall_blocks_lots_lists_markets_and_exports(admin, refs):
    recall = admin.ok(
        "POST", "/recalls", {"lot_no": "ET-2026-001", "reason": "Kabul testi: laboratuvar"}, status=201
    )
    assert {lot["lot_no"]: lot["status"] for lot in recall["lots"]} == {
        "ET-2026-001": "BLOKE",
        "SUC-2026-045": "BLOKE",
    }
    assert {r["customer"]: D(r["qty"]) for r in recall["recipients"]} == {
        "Market A": D(30),
        "Market B": D(25),
        "Market C": D(30),
    }

    export = admin.get(f"/recalls/{recall['id']}/export.csv")
    assert export.status == 200 and export.headers.get("content-type", "").startswith("text/csv")
    rows = list(csv.reader(io.StringIO(export.body), delimiter=";"))
    names = {row[2] for row in rows[1:]}
    assert {"Market A", "Market B", "Market C", "Market B Şube 1", "Market B Şube 2"} <= names

    # Market A 5 paket iade eder: bloke lota iade alınır, ama lot hiçbir yere gönderilemez.
    line_a = by_customer(recall["recipients"])["Market A"]["sales"][0]["sale_line_id"]
    admin.ok("POST", "/returns", {"sale_line_id": line_a, "qty": "5"}, status=201)
    moved = admin.post(
        "/transfers",
        {
            "from_warehouse_id": refs["warehouse"]["ANA"],
            "to_warehouse_id": refs["warehouse"]["ARAC-01"],
            "lines": [{"lot_no": "SUC-2026-045", "qty": "1"}],
        },
    )
    assert moved.status == 409 and moved.code == "LOT_BLOCKED"
    produced = admin.post(
        "/production-orders",
        {
            "subcontractor_id": refs["partner"]["FSN-01"],
            "output_product_id": refs["product"]["NARIN-SUCUK"],
            "planned_qty": "5",
            "inputs": [{"lot_no": "SUC-2026-045", "qty": "5"}],
        },
    )
    assert produced.status == 409 and produced.code == "LOT_BLOCKED"


def test_at12_offline_sale_of_a_recalled_lot_is_flagged(admin, seller, refs):
    recall = admin.ok(
        "POST", "/recalls", {"lot_no": "KUZU-2026-012", "reason": "Kabul testi: veteriner"}, status=201
    )
    pulled = seller.ok("GET", "/sync/pull?since=0")
    blocked = {lot["lot_no"] for lot in pulled["lots"] if lot["status"] == "BLOKE"}
    but = next(lot["lot_no"] for lot in recall["lots"] if lot["lot_no"].startswith("BUT-"))
    assert but in blocked  # cihaz bir sonraki eşitlemede lotu bloke görür

    sale = {
        "client_uuid": str(uuid.uuid4()),
        "customer_id": refs["partner"]["M-C"],
        "warehouse_id": refs["warehouse"]["ARAC-01"],
        "sold_at": f"{TODAY}T11:00:00+03:00",
        "lines": [{"lot_no": but, "qty": "2", "unit_price": "22.00"}],
    }
    [result] = seller.ok("POST", "/sync/push", {"device_id": "kabul-cevrimdisi", "sales": [sale]})["results"]
    assert result["status"] == "ACCEPTED_WITH_WARNING"
    detail = admin.ok("GET", f"/recalls/{recall['id']}")
    assert [(r["customer"], r["lot_no"]) for r in detail["recipients"] if r["recall_violation"]] == [
        ("Market C", but)
    ]
    assert any(but in a["message"] for a in admin.ok("GET", "/alerts?only_open=true"))


def test_at10_ledger_corrections_and_integrity(admin, refs):
    parts = STATE["at03_parts"]
    main = refs["warehouse"]["ANA"]
    too_much = admin.post(
        "/transfers",
        {
            "from_warehouse_id": main,
            "to_warehouse_id": refs["warehouse"]["ARAC-01"],
            "lines": [{"lot_no": parts["KUZU-OMUZ"], "qty": "999"}],
        },
    )
    assert too_much.status == 409 and too_much.code == "INSUFFICIENT_STOCK"
    admin.ok(
        "POST",
        "/adjustments",
        {"lot_no": parts["KUZU-OMUZ"], "warehouse_id": main, "qty": "1", "reason": "Kabul testi"},
        status=201,
    )
    fire = next(m for m in admin.ok("GET", f"/lots/{parts['KUZU-OMUZ']}/movements") if m["type"] == "FIRE")
    reversal = admin.ok(
        "POST", f"/movements/{fire['id']}/reverse", {"reason": "Kabul testi: yanlış lot"}, status=201
    )
    assert [(m["type"], D(m["qty"])) for m in reversal] == [("TERS_KAYIT", D(1))]
    assert D(admin.ok("GET", f"/lots/{parts['KUZU-OMUZ']}")["remaining_qty"]) == D(5)
    integrity = admin.ok("GET", "/reports/integrity")
    assert [row["ok"] for row in integrity["rows"]] == [True] * 8, integrity["rows"]


# --- Yapay zekâ ve raporlar


def test_at13_ai_models_beat_the_baseline_and_are_recorded_live(admin):
    body = admin.ok("GET", "/ai/evaluation")
    a, b = body["metadata"]["model_a"]["test"], body["metadata"]["model_b"]["test"]
    assert a["model"]["packages_mae"] < a["baseline"]["packages_mae"]
    assert a["model"]["ekp_mae_eur"] < a["baseline"]["ekp_mae_eur"]
    assert b["model"]["mae_kg"] < b["baseline"]["mae_kg"]
    assert body["metadata"]["limitations"]
    documents = {r["document_no"] for r in body["real"]}
    assert {"URT-2026-045", STATE["at01_order"]["order_no"]} <= documents
    assert STATE["at01_order"]["forecast"]["model_version"].startswith("A-")


@pytest.mark.parametrize(
    "code", ["purchases", "production", "cuttings", "lot-movements", "sales", "recalls", "integrity"]
)
def test_reports_are_filled_and_download_as_csv(admin, code):
    report = admin.ok("GET", f"/reports/{code}")
    assert report["rows"], f"{code} raporu boş"
    export = admin.get(f"/reports/{code}?format=csv")
    assert export.status == 200 and export.headers.get("content-type", "").startswith("text/csv")


def test_summary_line():
    """Kabul raporu için: izleme süresi ve sınanan sistem adresi."""
    print(f"\nSistem: {BASE} · ET-2026-001 ileri izleme süresi: {STATE.get('trace_seconds', 0):.3f} sn")
