"""Kalite blokesi (karantina) ve geri çağırmada müşteri iletişim kaydı."""

import csv
import io

import pytest
from sqlalchemy import select

from app.demo import build_demo_scenario
from app.models import AuditEvent, Partner, Warehouse
from tests.helpers import auth_header, by_code, make_lot

API = "/api/v1"


@pytest.fixture
def quality(client):
    return auth_header(client, "kalite1", "kalite123")


@pytest.fixture
def demo(session):
    build_demo_scenario(session)
    session.flush()


def store_sale(client, session, lot_no):
    store = auth_header(client, "magaza1", "magaza123")
    return client.post(
        f"{API}/sales",
        json={
            "customer_id": by_code(session, Partner, "PERAKENDE").id,
            "warehouse_id": by_code(session, Warehouse, "ANA").id,
            "payment_method": "NAKIT",
            "lines": [{"lot_no": lot_no, "qty": "1", "unit_price": "24.90"}],
        },
        headers=store,
    )


def lot(client, headers, lot_no):
    return client.get(f"{API}/lots/{lot_no}", headers=headers).json()


def test_quality_hold_closes_the_lot_until_released(client, session, quality):
    make_lot(session, "KARANTINA-1")
    held = client.post(f"{API}/lots/KARANTINA-1/hold", json={"reason": "Ambalajda şişme"}, headers=quality)
    assert held.status_code == 200 and held.json()["status"] == "BLOKE"
    [hold] = held.json()["holds"]
    assert hold["reason"] == "Ambalajda şişme" and hold["released_at"] is None and hold["placed_by_name"]

    blocked = store_sale(client, session, "KARANTINA-1")
    assert blocked.status_code == 409 and blocked.json()["error"]["code"] == "LOT_BLOCKED"

    released = client.post(
        f"{API}/lots/KARANTINA-1/release", json={"note": "Laboratuvar temiz"}, headers=quality
    )
    assert released.status_code == 200 and released.json()["status"] == "AKTIF"
    assert released.json()["holds"][0]["release_note"] == "Laboratuvar temiz"
    assert store_sale(client, session, "KARANTINA-1").status_code == 201
    actions = set(session.scalars(select(AuditEvent.action)))
    assert {"KALITE_BLOKESI", "KALITE_BLOKESI_KALDIRILDI"} <= actions


def test_hold_and_recall_do_not_release_each_other(client, quality, demo):
    client.post(f"{API}/lots/SUC-2026-045/hold", json={"reason": "Tat şikâyeti"}, headers=quality)
    first = client.post(
        f"{API}/recalls", json={"lot_no": "ET-2026-001", "reason": "Laboratuvar"}, headers=quality
    )
    client.post(f"{API}/recalls/{first.json()['id']}/close", json={"resolution": "SERBEST"}, headers=quality)
    assert lot(client, quality, "ET-2026-001")["status"] == "AKTIF"
    assert lot(client, quality, "SUC-2026-045")["status"] == "BLOKE"  # kalite blokesi sürüyor

    second = client.post(
        f"{API}/recalls", json={"lot_no": "ET-2026-001", "reason": "Yeniden"}, headers=quality
    )
    released = client.post(f"{API}/lots/SUC-2026-045/release", json={}, headers=quality).json()
    assert released["status"] == "BLOKE" and released["open_recalls"] == [second.json()["recall_no"]]


def test_hold_rules(client, session, quality):
    make_lot(session, "KARANTINA-2")
    assert (
        client.post(f"{API}/lots/KARANTINA-2/hold", json={"reason": "  "}, headers=quality).status_code == 422
    )
    assert client.post(f"{API}/lots/KARANTINA-2/release", json={}, headers=quality).status_code == 409
    assert (
        client.post(f"{API}/lots/KARANTINA-2/hold", json={"reason": "Şüphe"}, headers=quality).status_code
        == 200
    )
    again = client.post(f"{API}/lots/KARANTINA-2/hold", json={"reason": "Şüphe"}, headers=quality)
    assert again.status_code == 409 and again.json()["error"]["code"] == "INVALID_STATE"
    depot = auth_header(client, "depo1", "depo1234")
    assert client.post(f"{API}/lots/KARANTINA-2/release", json={}, headers=depot).status_code == 403


def test_recall_contact_log_tracks_each_customer(client, session, quality, demo):
    recall = client.post(
        f"{API}/recalls", json={"lot_no": "ET-2026-001", "reason": "Lab"}, headers=quality
    ).json()
    url = f"{API}/recalls/{recall['id']}/contacts"
    market = {code: by_code(session, Partner, code).id for code in ("M-A", "M-B")}
    assert recall["contact_counts"] == {"reached": 0, "unreached": 0, "pending": 3}

    first = client.post(
        url, json={"partner_id": market["M-A"], "outcome": "ULASILDI", "note": "Ayırdı"}, headers=quality
    )
    assert first.status_code == 201
    body = client.post(
        url, json={"partner_id": market["M-B"], "outcome": "ULASILAMADI"}, headers=quality
    ).json()
    assert body["contact_counts"] == {"reached": 1, "unreached": 1, "pending": 1}
    assert [(c["customer"], c["outcome"]) for c in body["contacts"]] == [
        ("Market B", "ULASILAMADI"),
        ("Market A", "ULASILDI"),
    ]
    body = client.post(
        url, json={"partner_id": market["M-B"], "outcome": "URUN_KALMADI"}, headers=quality
    ).json()
    assert body["contact_counts"] == {"reached": 2, "unreached": 0, "pending": 1}  # son kayıt geçerli

    text = client.get(f"{API}/recalls/{recall['id']}/export.csv", headers=quality).content.decode("utf-8-sig")
    rows = {row[2]: row for row in csv.reader(io.StringIO(text), delimiter=";")}
    assert rows["Alıcı"][14] == "Son iletişim"
    assert rows["Market A"][14].startswith("Ulaşıldı (") and rows["Market C"][14] == "Bekliyor"

    outsider = by_code(session, Partner, "TED-ET").id
    wrong = client.post(url, json={"partner_id": outsider, "outcome": "ULASILDI"}, headers=quality)
    assert wrong.status_code == 422
    client.post(f"{API}/recalls/{recall['id']}/close", json={"resolution": "SERBEST"}, headers=quality)
    closed = client.post(url, json={"partner_id": market["M-A"], "outcome": "ULASILDI"}, headers=quality)
    assert closed.status_code == 409
    assert session.scalars(select(AuditEvent).where(AuditEvent.action == "GERI_CAGIRMA_ILETISIM")).first()
