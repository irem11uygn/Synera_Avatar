"""Yapay zekâ entegrasyonu (FR-501…FR-504, TR-006): tahmin kaydı, sapma, model yokken iş akışı."""

from decimal import Decimal as D

import pytest
from avatar_ml import predict
from sqlalchemy import select

from app.demo import build_demo_scenario
from app.models import AiForecast, CuttingRecipe, Partner, Product, ProductionOrder
from app.models.enums import ForecastTarget
from tests.helpers import auth_header, by_code

API = "/api/v1"
INPUTS = [
    {"lot_no": "ET-2026-001", "qty": "100"},
    {"lot_no": "BAH-2026-014", "qty": "2"},
    {"lot_no": "BAG-2026-007", "qty": "5"},
]


@pytest.fixture
def admin(client):
    return auth_header(client, "yonetici", "yonetici123")


def order_body(session) -> dict:
    return {
        "subcontractor_id": by_code(session, Partner, "FSN-01").id,
        "output_product_id": by_code(session, Product, "NARIN-SUCUK").id,
        "planned_qty": "85",
        "service_unit_price": "5.50",
        "inputs": INPUTS,
    }


def test_model_a_forecast_is_recorded_when_the_order_opens(client, admin, session):
    body = client.post(f"{API}/production-orders", json=order_body(session), headers=admin).json()
    forecast = body["forecast"]
    assert forecast["model_version"].startswith("A-")
    assert 75 <= D(forecast["expected_qty"]) <= 92  # senaryo koşullarında verim ≈ %85
    assert D("15") < D(forecast["ekp"]) < D("21")
    assert forecast["qty_deviation"] is None  # henüz kabul yok
    record = session.scalars(
        select(AiForecast).where(AiForecast.target_type == ForecastTarget.URETIM_EMRI)
    ).one()
    assert record.features["meat_kg"] == 100.0 and record.features["subcontractor"] == "FSN-01"


def test_deviation_appears_after_acceptance(client, admin, session):
    build_demo_scenario(session)
    order = session.scalars(select(ProductionOrder).where(ProductionOrder.order_no == "URT-2026-045")).one()
    body = client.get(f"{API}/production-orders/{order.id}", headers=admin).json()
    forecast = body["forecast"]
    assert D(forecast["qty_deviation"]) == D(85) - D(forecast["expected_qty"])
    assert D(forecast["ekp_deviation"]) == (D(body["cost"]["ekp"]) - D(forecast["ekp"])).quantize(D("0.01"))


def test_model_b_fills_expected_kg_on_every_line(client, admin, session):
    body = client.post(
        f"{API}/cuttings",
        json={
            "recipe_id": by_code(session, CuttingRecipe, "KUZU-STD").id,
            "input_lot_no": "KUZU-2026-012",
            "input_qty": "25",
        },
        headers=admin,
    ).json()
    predicted = [D(line["predicted_kg"]) for line in body["lines"]]
    assert all(p > 0 for p in predicted)
    assert abs(sum(predicted) - D(25)) <= D("0.01")  # paylar toplamı 1


def test_forecast_endpoints_do_not_write(client, admin, session):
    a = client.post(f"{API}/ai/production-forecast", json=order_body(session), headers=admin)
    assert a.status_code == 200, a.text
    assert D(a.json()["raw_material_cost"]) == D("1076.00")  # 970 + 48 + 58: tahmin değil, lot değerleri
    b = client.post(
        f"{API}/ai/cutting-forecast",
        json={
            "recipe_id": by_code(session, CuttingRecipe, "KUZU-STD").id,
            "input_lot_no": "KUZU-2026-012",
            "input_qty": "25",
        },
        headers=admin,
    )
    assert b.status_code == 200, b.text
    standard = {line["key"]: D(line["standard_kg"]) for line in b.json()["lines"]}
    assert standard["KUZU-BUT"] == D("6.750")  # 0,27 × 25
    assert session.scalars(select(AiForecast)).all() == []


def test_evaluation_reports_baseline_and_model_errors(client, admin, session):
    build_demo_scenario(session)
    body = client.get(f"{API}/ai/evaluation", headers=admin).json()
    assert body["available"] is True
    test_a = body["metadata"]["model_a"]["test"]
    assert set(test_a) == {"baseline", "model", "improvement_pct"}
    assert body["metadata"]["limitations"]
    assert {r["model"] for r in body["real"]} == {"A", "B"}
    assert any(r["document_no"] == "URT-2026-045" and r["item"] == "Paket sayısı" for r in body["real"])


def test_missing_model_never_blocks_the_workflow(client, admin, session, monkeypatch):
    def unavailable(*_args, **_kwargs):
        raise predict.ModelUnavailable("model_a.joblib bulunamadı")

    monkeypatch.setattr(predict, "production_yield", unavailable)
    response = client.post(f"{API}/production-orders", json=order_body(session), headers=admin)
    assert response.status_code == 201, response.text
    assert response.json()["forecast"] is None
    assert (
        client.post(f"{API}/ai/production-forecast", json=order_body(session), headers=admin).status_code
        == 404
    )
