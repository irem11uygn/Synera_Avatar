"""Ayarlar ekranının sunucu tarafı: açık oturumlarım, diğer cihazlardan çıkış ve telefonda geçici şifre."""

from sqlalchemy import select

from app.models import AuditEvent, Warehouse
from tests.helpers import auth_header, by_code

API = "/api/v1"


def test_my_sessions_list_marks_this_device_and_hides_tokens(client):
    first = auth_header(client, "depo1", "depo1234")
    second = auth_header(client, "depo1", "depo1234")
    auth_header(client, "kalite1", "kalite123")  # başkasının oturumu listede görünmez

    rows = client.get(f"{API}/auth/sessions", headers=second).json()
    assert len(rows) == 2 and [row["current"] for row in rows].count(True) == 1
    assert set(rows[0]) == {"started_at", "expires_at", "current"}  # belirteç ya da özeti dönmez
    assert client.get(f"{API}/auth/sessions", headers=first).status_code == 200


def test_close_other_sessions_keeps_only_this_one(client, session):
    other_device = auth_header(client, "depo1", "depo1234")
    this_device = auth_header(client, "depo1", "depo1234")

    response = client.post(f"{API}/auth/sessions/close-others", headers=this_device)
    assert response.status_code == 200 and response.json() == {"closed": 1}
    assert client.get(f"{API}/auth/me", headers=other_device).status_code == 401
    assert client.get(f"{API}/auth/me", headers=this_device).status_code == 200
    assert [row["current"] for row in client.get(f"{API}/auth/sessions", headers=this_device).json()] == [
        True
    ]
    event = session.scalars(select(AuditEvent).where(AuditEvent.action == "OTURUMLAR_KAPATILDI")).one()
    assert event.username == "depo1"


def test_session_endpoints_need_login(client):
    assert client.get(f"{API}/auth/sessions").status_code == 401
    assert client.post(f"{API}/auth/sessions/close-others").status_code == 401


def test_new_phone_user_can_replace_temporary_password_and_then_sync(client, session):
    """Satış elemanı web'e giremez; geçici şifresini telefondan değiştirebilmeli (yoksa hiç çalışamaz)."""
    admin = auth_header(client, "yonetici", "yonetici123")
    van = by_code(session, Warehouse, "ARAC-01")
    created = client.post(
        f"{API}/users",
        json={
            "username": "satis2",
            "full_name": "Satış İki",
            "role": "SATIS",
            "password": "gecici123",
            "warehouse_id": van.id,
        },
        headers=admin,
    )
    assert created.status_code == 201, created.text

    login = client.post(f"{API}/auth/login", json={"username": "satis2", "password": "gecici123"}).json()
    assert login["user"]["must_change_password"] is True
    phone = {"Authorization": f"Bearer {login['token']}"}
    blocked = client.get(f"{API}/sync/pull", params={"since": 0}, headers=phone)
    assert blocked.status_code == 403 and blocked.json()["error"]["code"] == "PASSWORD_CHANGE_REQUIRED"

    changed = client.post(
        f"{API}/auth/change-password",
        json={"current_password": "gecici123", "new_password": "kendisifrem9"},
        headers=phone,
    )
    assert changed.status_code == 200 and changed.json()["must_change_password"] is False
    assert client.get(f"{API}/sync/pull", params={"since": 0}, headers=phone).status_code == 200
