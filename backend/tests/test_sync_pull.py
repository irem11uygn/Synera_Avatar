"""Android'e çekme senkronizasyonu (FR-405, ADR-004)."""

from decimal import Decimal

from app.models import Warehouse
from app.models.enums import LotStatus
from app.services.ledger import post_transfer
from tests.helpers import auth_header, by_code, lot_by_no


def pull(client, headers, since=0):
    response = client.get("/api/v1/sync/pull", params={"since": since}, headers=headers)
    assert response.status_code == 200, response.text
    return response.json()


def load_van(session, lot_no: str, qty: str) -> None:
    post_transfer(
        session,
        lot_id=lot_by_no(session, lot_no).id,
        from_warehouse_id=by_code(session, Warehouse, "ANA").id,
        to_warehouse_id=by_code(session, Warehouse, "ARAC-01").id,
        qty=Decimal(qty),
        doc_id=1,
    )


def test_first_pull_returns_master_data_and_empty_van(client):
    body = pull(client, auth_header(client, "satis1", "satis123"))
    assert len(body["products"]) == 10
    assert [c["name"] for c in body["customers"]] == ["Market A", "Market B", "Market C"]
    assert (body["lots"], body["stock"]) == ([], [])
    sucuk = next(p for p in body["products"] if p["code"] == "NARIN-SUCUK")
    assert (sucuk["sale_price"], sucuk["unit_weight_kg"], sucuk["base_unit"]) == ("24.90", "1.000", "ADET")
    assert body["next_since"] > 0


def test_next_pull_returns_only_what_changed_in_the_van(client, session):
    headers = auth_header(client, "satis1", "satis123")
    since = pull(client, headers)["next_since"]
    assert pull(client, headers, since)["products"] == []

    load_van(session, "ET-2026-001", "10")
    body = pull(client, headers, since)
    assert [lot["lot_no"] for lot in body["lots"]] == ["ET-2026-001"]
    assert body["stock"] == [{"lot_id": lot_by_no(session, "ET-2026-001").id, "qty": "10.000"}]
    assert body["products"] == [] and body["customers"] == []
    assert body["next_since"] > since


def test_blocked_lot_reaches_the_device(client, session):
    """Geri çağırma bilgisi: lot durumu değişince bir sonraki çekişte cihaza iner (FR-403)."""
    headers = auth_header(client, "satis1", "satis123")
    load_van(session, "ET-2026-001", "10")
    since = pull(client, headers)["next_since"]

    lot_by_no(session, "ET-2026-001").status = LotStatus.BLOKE
    session.flush()

    lots = pull(client, headers, since)["lots"]
    assert [(lot["lot_no"], lot["status"]) for lot in lots] == [("ET-2026-001", "BLOKE")]


def test_only_sales_users_can_pull(client):
    response = client.get("/api/v1/sync/pull", headers=auth_header(client, "yonetici", "yonetici123"))
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "FORBIDDEN"


def test_negative_since_is_rejected(client):
    headers = auth_header(client, "satis1", "satis123")
    assert client.get("/api/v1/sync/pull", params={"since": -1}, headers=headers).status_code == 422
