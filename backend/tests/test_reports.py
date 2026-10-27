"""Raporlar (FR-601…FR-607): demo verisiyle dolu, süzgeçler ve CSV."""

import csv
import io
from decimal import Decimal as D

import pytest

from app.demo import build_demo_scenario
from app.models import Product
from tests.helpers import auth_header, by_code

URL = "/api/v1/reports"


@pytest.fixture
def admin(client):
    return auth_header(client, "yonetici", "yonetici123")


@pytest.fixture
def demo(session):
    build_demo_scenario(session)
    session.flush()


def report(client, admin, code, **params) -> dict:
    response = client.get(f"{URL}/{code}", params=params, headers=admin)
    assert response.status_code == 200, response.text
    return response.json()


def test_report_list_names_all_seven(client, admin):
    codes = [r["code"] for r in client.get(URL, headers=admin).json()]
    assert codes == ["purchases", "production", "cuttings", "lot-movements", "sales", "recalls", "integrity"]


def test_purchase_report_lot_value_includes_extra_costs(client, admin, demo):
    body = report(client, admin, "purchases")
    rows = {row["lot_no"]: row for row in body["rows"]}
    assert D(rows["KUZU-2026-012"]["lot_value"]) == D("351.00")  # 287,50 fatura + 63,50 ek maliyet
    assert D(rows["ET-2026-001"]["invoice_amount"]) == D("970.00")
    assert D(body["totals"]["lot_value"]) == sum(D(r["lot_value"]) for r in body["rows"])


def test_production_report_shows_ekp_and_differences(client, admin, demo):
    [row] = report(client, admin, "production")["rows"]
    assert (row["order_no"], row["output_lot_no"], row["status"]) == (
        "URT-2026-045",
        "SUC-2026-045",
        "TAMAMLANDI",
    )
    assert (D(row["total_cost"]), D(row["ekp"]), D(row["qty_difference"])) == (D("1543.50"), D("18.16"), D(0))
    assert "ET-2026-001: sevk 100 / tüketim 100 / iade 0" in row["input_differences"]


def test_cutting_report_allocates_the_whole_cost(client, admin, demo):
    body = report(client, admin, "cuttings")
    assert {row["cutting_no"] for row in body["rows"]} == {"PRC-2026-012"}
    assert D(body["totals"]["allocated_cost"]) == D("351.00")
    fire = next(row for row in body["rows"] if row["line"] == "Fire")
    assert D(fire["actual_kg"]) == D(3) and fire["output_lot_no"] is None


def test_lot_movement_report_balance_equals_sum_of_movements(client, admin, demo):
    rows = report(client, admin, "lot-movements", lot_no="SUC-2026-045")["rows"]
    assert [r["type"] for r in rows][:1] == ["URETIM_GIRIS"]
    assert sum(D(r["qty"]) for r in rows) == D(rows[-1]["balance_qty"]) == D(0)
    assert {r["doc_no"] for r in rows} >= {"URT-2026-045", "SAT-2026-0101"}


def test_sales_report_and_product_filter(client, admin, session, demo):
    sucuk = by_code(session, Product, "NARIN-SUCUK").id
    body = report(client, admin, "sales", product_id=sucuk)
    assert [(r["customer"], D(r["qty"])) for r in body["rows"]] == [
        ("Market A", D(30)),
        ("Market B", D(25)),
        ("Market C", D(30)),
    ]
    assert D(body["totals"]["amount"]) == D("2116.50")  # 85 × 24,90
    assert D(body["totals"]["cost"]) == D("1543.50")
    assert report(client, admin, "sales", date_from="2020-01-01", date_to="2020-01-02")["rows"] == []


def test_recall_report_lists_markets_after_recall(client, admin, demo):
    client.post("/api/v1/recalls", json={"lot_no": "ET-2026-001", "reason": "Laboratuvar"}, headers=admin)
    rows = report(client, admin, "recalls")["rows"]
    assert sorted((r["customer"], D(r["qty"])) for r in rows) == [
        ("Market A", D(30)),
        ("Market B", D(25)),
        ("Market C", D(30)),
    ]
    assert {r["onward"] for r in rows} == {"KAYITLI", "BILINMIYOR"}


def test_integrity_report_is_all_green(client, admin, demo):
    body = report(client, admin, "integrity")
    assert [r["ok"] for r in body["rows"]] == [True] * 8
    assert body["notes"] == ["8/8 kural tutarlı."]


def test_reports_download_as_csv(client, admin, demo):
    response = client.get(f"{URL}/sales", params={"format": "csv"}, headers=admin)
    assert response.status_code == 200 and response.headers["content-type"].startswith("text/csv")
    rows = list(csv.reader(io.StringIO(response.content.decode("utf-8-sig")), delimiter=";"))
    assert rows[0][:3] == ["Satış zamanı", "Belge", "Kanal"]
    assert any(row[3] == "Market B" and row[6] == "25" for row in rows[1:])


def test_sales_user_cannot_read_reports(client):
    seller = auth_header(client, "satis1", "satis123")
    assert client.get(f"{URL}/sales", headers=seller).status_code == 403
