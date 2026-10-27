"""Ana veri, alış, lot ve transfer API'leri (FR-101…FR-104, FR-112, FR-207, FR-303)."""

from decimal import Decimal as D

import pytest

from app.models import Partner, Product, Warehouse
from tests.helpers import auth_header, by_code

API = "/api/v1"


@pytest.fixture
def admin(client):
    return auth_header(client, "yonetici", "yonetici123")


def test_lists_master_data(client, admin):
    assert len(client.get(f"{API}/products", headers=admin).json()) == 10
    assert [p["code"] for p in client.get(f"{API}/products?kind=MAMUL", headers=admin).json()] == [
        "NARIN-SUCUK"
    ]
    customers = client.get(f"{API}/partners?role=customer", headers=admin).json()
    assert [c["name"] for c in customers] == ["Market A", "Market B", "Market C", "Perakende müşteri"]
    assert [w["code"] for w in client.get(f"{API}/warehouses", headers=admin).json()] == [
        "ANA",
        "DIS-FSN-01",
        "ARAC-01",
    ]


def test_product_card_create_update_and_rules(client, admin):
    body = {
        "code": "SUCUK-500",
        "name": "Narin Sucuk 500 g",
        "kind": "MAMUL",
        "base_unit": "ADET",
        "unit_weight_kg": "0.500",
    }
    created = client.post(f"{API}/products", json=body, headers=admin)
    assert created.status_code == 201, created.text
    duplicate = client.post(f"{API}/products", json=body, headers=admin)
    assert (duplicate.status_code, "zaten" in duplicate.json()["error"]["message"]) == (422, True)

    updated = client.put(
        f"{API}/products/{created.json()['id']}", json={**body, "sale_price": "13.50"}, headers=admin
    )
    assert D(updated.json()["sale_price"]) == D("13.50")

    no_weight = {**body, "code": "X-1", "unit_weight_kg": None}
    assert client.post(f"{API}/products", json=no_weight, headers=admin).status_code == 422


def test_partner_card_with_contact_details(client, admin):
    body = {
        "code": "M-D",
        "name": "Market D",
        "is_customer": True,
        "phone": "+90 000 000 03 04",
        "email": "d@example.com",
    }
    response = client.post(f"{API}/partners", json=body, headers=admin)
    assert (response.status_code, response.json()["email"]) == (201, "d@example.com")


def test_new_subcontractor_gets_its_own_warehouse(client, admin):
    """Web'den açılan dış üreticiyle hemen emir açılabilmeli: sevk onun deposuna yapılır (FR-106)."""
    body = {"code": "FSN-02", "name": "İkinci Fason", "is_subcontractor": True}
    partner = client.post(f"{API}/partners", json=body, headers=admin).json()
    warehouses = client.get(f"{API}/warehouses", headers=admin).json()
    own = [w for w in warehouses if w["partner_id"] == partner["id"]]
    assert [(w["code"], w["kind"]) for w in own] == [("DIS-FSN-02", "DIS_URETICI")]
    # İkinci kayıtta yeni depo açılmaz.
    client.put(f"{API}/partners/{partner['id']}", json=body, headers=admin)
    assert len(client.get(f"{API}/warehouses", headers=admin).json()) == len(warehouses)


def test_purchase_creates_lot_with_real_total_cost(client, admin, session):
    body = {
        "supplier_id": by_code(session, Partner, "TED-KUZU").id,
        "doc_no": "FAT-KUZU-2026-0240",
        "doc_date": "2026-10-25",
        "lines": [
            {
                "product_id": by_code(session, Product, "KUZU-BUTUN").id,
                "lot_no": "KUZU-2026-013",
                "qty": "25",
                "unit_price": "11.50",
                "extra_costs": [{"kind": "KESIM", "amount": "40.00"}, {"kind": "NAKLIYE", "amount": "23.50"}],
            }
        ],
    }
    response = client.post(f"{API}/purchases", json=body, headers=admin)
    assert response.status_code == 201, response.text
    line = response.json()["lines"][0]
    assert (D(line["computed_amount"]), D(line["lot_value"]), line["expiry_date"]) == (
        D("287.50"),
        D("351.00"),
        "2026-10-30",
    )
    assert len(client.get(f"{API}/purchases", headers=admin).json()) == 5  # 4 örnek + 1 yeni


def test_purchase_invoice_mismatch_needs_explanation(client, admin, session):
    body = {
        "supplier_id": by_code(session, Partner, "TED-KUZU").id,
        "doc_no": "FAT-1",
        "doc_date": "2026-10-25",
        "lines": [
            {
                "product_id": by_code(session, Product, "KUZU-BUTUN").id,
                "lot_no": "KUZU-2026-014",
                "qty": "25",
                "unit_price": "11.50",
                "invoice_amount": "351.00",
            }
        ],
    }
    response = client.post(f"{API}/purchases", json=body, headers=admin)
    assert (response.status_code, response.json()["error"]["code"]) == (422, "AMOUNT_MISMATCH_NOTE_REQUIRED")


def test_lot_detail_balances_and_history(client, admin):
    lots = client.get(f"{API}/lots", params={"q": "ET-2026"}, headers=admin).json()
    assert [lot["lot_no"] for lot in lots] == ["ET-2026-001"]
    detail = client.get(f"{API}/lots/ET-2026-001", headers=admin).json()
    assert (detail["supplier_name"], D(detail["unit_cost"])) == ("Örnek Et Tedarik", D("9.70"))
    assert [(b["warehouse_code"], D(b["qty"])) for b in detail["balances"]] == [("ANA", D("100"))]
    history = client.get(f"{API}/lots/ET-2026-001/movements", headers=admin).json()
    assert [(m["type"], D(m["qty"]), D(m["value"]), m["doc_no"]) for m in history] == [
        ("ALIS_GIRIS", D("100"), D("970.00"), "FAT-ET-2026-0412")
    ]
    assert history[0]["posted_at"].endswith("Z")  # UTC, saat dilimi ekiyle (api.md §1)


def test_unknown_lot_is_404_in_turkish(client, admin):
    response = client.get(f"{API}/lots/YOK-1", headers=admin)
    assert (response.status_code, response.json()["error"]["message"]) == (404, "YOK-1 lotu bulunamadı.")


def test_loading_the_van_is_a_transfer(client, admin, session):
    body = {
        "from_warehouse_id": by_code(session, Warehouse, "ANA").id,
        "to_warehouse_id": by_code(session, Warehouse, "ARAC-01").id,
        "lines": [{"lot_no": "ET-2026-001", "qty": "10"}],
    }
    response = client.post(f"{API}/transfers", json=body, headers=admin)
    assert response.status_code == 201, response.text
    assert (response.json()["transfer_no"], response.json()["reason"]) == ("TRF-2026-0001", "ARAC_YUKLEME")
    detail = client.get(f"{API}/lots/ET-2026-001", headers=admin).json()
    assert {b["warehouse_code"]: D(b["qty"]) for b in detail["balances"]} == {
        "ANA": D("90"),
        "ARAC-01": D("10"),
    }
    assert D(detail["remaining_value"]) == D("970.00")  # transfer değer taşımaz

    # Hareket geçmişi kimin, hangi belgeyle yaptığını gösterir (FR-112).
    history = client.get(f"{API}/lots/ET-2026-001/movements", headers=admin).json()
    assert [(m["type"], m["warehouse_code"], m["doc_no"], m["user_name"]) for m in history[1:]] == [
        ("TRANSFER_CIKIS", "ANA", "TRF-2026-0001", "Demo Yönetici"),
        ("TRANSFER_GIRIS", "ARAC-01", "TRF-2026-0001", "Demo Yönetici"),
    ]

    # Depo kırılımında stok (FR-104).
    van = by_code(session, Warehouse, "ARAC-01").id
    rows = client.get(f"{API}/stock", params={"warehouse_id": van}, headers=admin).json()
    assert [(r["lot_no"], r["warehouse_code"], D(r["qty"]), r["base_unit"]) for r in rows] == [
        ("ET-2026-001", "ARAC-01", D("10"), "KG")
    ]
    everywhere = client.get(f"{API}/stock", headers=admin).json()
    assert sum(D(r["qty"]) for r in everywhere if r["lot_no"] == "ET-2026-001") == D("100")


def test_master_data_is_for_managers_only(client):
    assert client.get(f"{API}/products", headers=auth_header(client, "satis1", "satis123")).status_code == 403
