"""Görev 2 — kuzu parçalama API'si (AT-03, AT-04; FR-201…FR-208)."""

from decimal import Decimal as D

import pytest

from app.models import CuttingRecipe, Product
from app.models.enums import LotStatus
from app.services.integrity import check_invariants
from app.services.lot_graph import descendants
from tests.helpers import auth_header, by_code, lot_by_no

URL = "/api/v1/cuttings"
PARTS = {"KUZU-BUT": "7", "KUZU-SIRT": "4", "KUZU-OMUZ": "5", "KUZU-KABURGA": "3", "KUZU-KIYMA": "3"}


@pytest.fixture
def admin(client):
    return auth_header(client, "yonetici", "yonetici123")


def new_cutting(client, admin, session, *, qty="25", lot_no="KUZU-2026-012", method=None):
    body = {
        "recipe_id": by_code(session, CuttingRecipe, "KUZU-STD").id,
        "input_lot_no": lot_no,
        "input_qty": qty,
    }
    if method:
        body["method"] = method
    return client.post(URL, json=body, headers=admin)


def created(client, admin, session, **kwargs) -> dict:
    response = new_cutting(client, admin, session, **kwargs)
    assert response.status_code == 201, response.text
    return response.json()


def weighed(cutting: dict, *, parts=PARTS, fire: str | None = "3") -> list[dict]:
    """Reçete satırlarına fiili kg'ları yerleştirir; fire=None → fire tartılmadı."""
    outputs = []
    for line in cutting["lines"]:
        qty = fire if line["line_type"] == "FIRE" else parts.get(line["product_code"])
        outputs.append({"recipe_line_id": line["recipe_line_id"], "actual_qty": qty})
    return outputs


def record(client, admin, cutting, outputs, method=None) -> dict:
    body = {"outputs": outputs, **({"method": method} if method else {})}
    response = client.put(f"{URL}/{cutting['id']}", json=body, headers=admin)
    assert response.status_code == 200, response.text
    return response.json()


def approve(client, admin, cutting):
    return client.post(f"{URL}/{cutting['id']}/approve", headers=admin)


def shares(body: dict) -> list[tuple[str | None, D | None]]:
    return [
        (line["product_code"], line["allocated_cost"] and D(line["allocated_cost"])) for line in body["lines"]
    ]


def test_seed_recipe_is_listed_with_ratios_summing_to_one(client, admin):
    recipes = client.get("/api/v1/cutting-recipes", headers=admin).json()
    assert [r["code"] for r in recipes] == ["KUZU-STD"]
    lines = recipes[0]["lines"]
    assert [line["product_code"] for line in lines] == [*PARTS, None]
    assert sum(D(line["standard_ratio"]) for line in lines) == 1
    assert (lines[-1]["line_type"], lines[-1]["bears_cost"]) == ("FIRE", False)


def test_draft_opens_recipe_lines_and_shows_expected_cost(client, admin, session):
    cutting = created(client, admin, session)
    assert (cutting["cutting_no"], cutting["status"], cutting["method"]) == (
        "PRC-2026-012",
        "TASLAK",
        "DEGER",
    )
    assert D(cutting["total_cost"]) == D("351.00")  # alış 287,50 + kesim 40,00 + nakliye 23,50 (FR-203)
    cost = cutting["input_cost"]
    assert (D(cost["computed_amount"]), [D(c["amount"]) for c in cost["extra_costs"]]) == (
        D("287.50"),
        [D("40.00"), D("23.50")],
    )
    but = cutting["lines"][0]
    assert (D(but["standard_kg"]), but["actual_kg"], but["allocated_cost"]) == (D("6.750"), None, None)
    assert cutting["balance"]["missing_lines"] == 6 and cutting["balance"]["ok"] is False
    assert lot_by_no(session, "KUZU-2026-012").remaining_qty == D("25")  # taslak deftere yazmaz


def test_at03_value_weighted_allocation_end_to_end(client, admin, session):
    cutting = created(client, admin, session)
    body = record(client, admin, cutting, weighed(cutting))
    assert body["balance"]["ok"] is True
    assert shares(body) == [
        ("KUZU-BUT", D("123.41")),
        ("KUZU-SIRT", D("83.34")),
        ("KUZU-OMUZ", D("72.12")),
        ("KUZU-KABURGA", D("33.66")),
        ("KUZU-KIYMA", D("38.47")),
        (None, D("0.00")),  # fire maliyet almaz
    ]
    assert D(body["allocated_total"]) == D("351.00")
    assert body["lines"][-1]["cost_per_kg"] is None  # fireye birim maliyet yazılmaz

    response = approve(client, admin, cutting)
    assert response.status_code == 200, response.text
    done = response.json()
    assert (done["status"], D(done["total_cost"])) == ("ONAYLANDI", D("351.00"))
    lots = [line["output_lot_no"] for line in done["lines"]]
    assert lots == [
        "BUT-PRC-2026-012",
        "SIRT-PRC-2026-012",
        "OMUZ-PRC-2026-012",
        "KABURGA-PRC-2026-012",
        "KIYMA-PRC-2026-012",
        None,
    ]
    but = lot_by_no(session, "BUT-PRC-2026-012")
    assert (but.remaining_qty, but.remaining_value, but.unit_cost) == (D("7"), D("123.41"), D("17.6300"))
    kuzu = lot_by_no(session, "KUZU-2026-012")
    assert (kuzu.remaining_qty, kuzu.remaining_value) == (D("0"), D("0.00"))
    # İleri izleme: kuzu lotu → bütün parça lotları (FR-208); sözlük kendisini derinlik 0 ile içerir.
    parts = {lot_by_no(session, no).id for no in lots if no}
    assert set(descendants(session, kuzu.id)) == {kuzu.id, *parts}
    assert but.expiry_date is not None and but.expiry_date <= kuzu.expiry_date
    assert all(result.ok for result in check_invariants(session))  # I-5: Σ pay = toplam, denge


def test_at03_quantity_weighted_allocation(client, admin, session):
    cutting = created(client, admin, session, method="MIKTAR")
    body = record(client, admin, cutting, weighed(cutting))
    assert shares(body)[:5] == [
        ("KUZU-BUT", D("111.68")),
        ("KUZU-SIRT", D("63.82")),
        ("KUZU-OMUZ", D("79.77")),
        ("KUZU-KABURGA", D("47.87")),  # eşit kalanda reçete sırası öne geçer
        ("KUZU-KIYMA", D("47.86")),
    ]
    assert approve(client, admin, cutting).status_code == 200


def test_at04_missing_fire_blocks_approval(client, admin, session):
    """25 kg giriş, 22 kg parça: fire girilmeden onaylanmaz; 3 kg fire girilince onaylanır."""
    cutting = created(client, admin, session)
    record(client, admin, cutting, weighed(cutting, fire=None))
    response = approve(client, admin, cutting)
    assert (response.status_code, response.json()["error"]["code"]) == (422, "VALIDATION_ERROR")

    body = record(client, admin, cutting, weighed(cutting, fire="0"))
    assert (body["balance"]["ok"], D(body["balance"]["difference_kg"])) == (False, D("3.000"))
    response = approve(client, admin, cutting)
    assert (response.status_code, response.json()["error"]["code"]) == (409, "WEIGHT_IMBALANCE")
    assert D(response.json()["error"]["details"]["difference_kg"]) == D("3.000")
    assert lot_by_no(session, "KUZU-2026-012").remaining_qty == D("25")  # reddedilen onay iz bırakmaz

    record(client, admin, cutting, weighed(cutting, fire="3"))
    assert approve(client, admin, cutting).status_code == 200


def test_tolerance_accepts_small_scale_differences(client, admin, session):
    """Reçete toleransı 0,2 kg: 24,85 kg çıkış kabul, 24,7 kg reddedilir."""
    cutting = created(client, admin, session)
    body = record(client, admin, cutting, weighed(cutting, fire="2.85"))
    assert (body["balance"]["ok"], D(body["balance"]["difference_kg"])) == (True, D("0.150"))
    body = record(client, admin, cutting, weighed(cutting, fire="2.7"))
    assert body["balance"]["ok"] is False


def test_preview_calculates_without_saving(client, admin, session):
    cutting = created(client, admin, session)
    response = client.post(
        f"{URL}/{cutting['id']}/preview", json={"outputs": weighed(cutting)}, headers=admin
    )
    assert response.status_code == 200, response.text
    assert D(response.json()["allocated_total"]) == D("351.00")
    again = client.get(f"{URL}/{cutting['id']}", headers=admin).json()
    assert again["lines"][0]["actual_kg"] is None and again["allocated_total"] is None


def test_partial_cutting_takes_proportional_cost(client, admin, session):
    cutting = created(client, admin, session, qty="10")
    assert D(cutting["total_cost"]) == D("140.40")  # 351,00 × 10 / 25
    parts = {"KUZU-BUT": "3", "KUZU-SIRT": "2", "KUZU-OMUZ": "2", "KUZU-KABURGA": "1", "KUZU-KIYMA": "1"}
    record(client, admin, cutting, weighed(cutting, parts=parts, fire="1"))
    assert approve(client, admin, cutting).status_code == 200
    kuzu = lot_by_no(session, "KUZU-2026-012")
    assert (kuzu.remaining_qty, kuzu.remaining_value) == (D("15"), D("210.60"))


def test_approved_cutting_cannot_change(client, admin, session):
    cutting = created(client, admin, session)
    record(client, admin, cutting, weighed(cutting))
    assert approve(client, admin, cutting).status_code == 200
    assert approve(client, admin, cutting).json()["error"]["code"] == "INVALID_STATE"
    response = client.put(f"{URL}/{cutting['id']}", json={"outputs": weighed(cutting)}, headers=admin)
    assert response.json()["error"]["code"] == "INVALID_STATE"


def test_draft_rejects_wrong_lot_missing_stock_and_blocked_lot(client, admin, session):
    wrong = new_cutting(client, admin, session, lot_no="ET-2026-001")
    assert (wrong.status_code, wrong.json()["error"]["code"]) == (422, "VALIDATION_ERROR")
    too_much = new_cutting(client, admin, session, qty="30")
    assert (too_much.status_code, too_much.json()["error"]["code"]) == (409, "INSUFFICIENT_STOCK")
    lot_by_no(session, "KUZU-2026-012").status = LotStatus.BLOKE
    session.flush()
    assert new_cutting(client, admin, session).json()["error"]["code"] == "LOT_BLOCKED"


def test_new_recipe_is_validated(client, admin, session):
    def body(**changes):
        base = {
            "code": "KUZU-YARIM",
            "name": "Yarım kuzu",
            "input_product_id": by_code(session, Product, "KUZU-BUTUN").id,
            "species": "KUZU",
            "default_method": "MIKTAR",
            "tolerance_kg": "0.100",
            "lines": [
                {
                    "line_type": "PARCA",
                    "product_id": by_code(session, Product, "KUZU-BUT").id,
                    "standard_ratio": "0.6",
                },
                {"line_type": "FIRE", "standard_ratio": "0.4", "bears_cost": False},
            ],
        }
        return {**base, **changes}

    def post(payload):
        return client.post("/api/v1/cutting-recipes", json=payload, headers=admin)

    response = post(body())
    assert response.status_code == 201, response.text
    assert [line["sort_order"] for line in response.json()["lines"]] == [1, 2]
    bad_sum = body(code="X1", lines=[{**body()["lines"][0], "standard_ratio": "0.5"}, body()["lines"][1]])
    assert "toplamı 1" in post(bad_sum).json()["error"]["message"]
    fire_with_product = body(code="X2", lines=[body()["lines"][0], {**body()["lines"][1], "product_id": 1}])
    assert post(fire_with_product).status_code == 422
    value_without_price = body(code="X3", default_method="DEGER")
    assert "€/kg" in post(value_without_price).json()["error"]["message"]
    assert post(body()).json()["error"]["message"] == "Reçete kodu 'KUZU-YARIM' zaten kullanılıyor."


def test_sales_user_cannot_cut(client):
    headers = auth_header(client, "satis1", "satis123")
    assert client.get(URL, headers=headers).status_code == 403
