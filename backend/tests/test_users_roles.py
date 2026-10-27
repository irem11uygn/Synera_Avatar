"""Kullanıcı yönetimi, şifre kuralları, giriş sınırı ve rol yetkileri (orta ölçekli işletme)."""

import pytest

from app.models import Warehouse
from tests.helpers import auth_header, by_code

API = "/api/v1"


@pytest.fixture
def admin(client):
    return auth_header(client, "yonetici", "yonetici123")


def login(client, username, password):
    return client.post(f"{API}/auth/login", json={"username": username, "password": password})


def new_user(client, admin, **fields):
    body = {"username": "depo2", "full_name": "Depo İki", "role": "DEPO", "password": "baslangic12"} | fields
    return client.post(f"{API}/users", json=body, headers=admin)


def test_new_user_must_change_password_before_working(client, admin):
    response = new_user(client, admin)
    assert response.status_code == 201, response.text
    assert response.json()["must_change_password"] is True

    token = login(client, "depo2", "baslangic12").json()["token"]
    headers = {"Authorization": f"Bearer {token}"}
    blocked = client.get(f"{API}/stock", headers=headers)
    assert (blocked.status_code, blocked.json()["error"]["code"]) == (403, "PASSWORD_CHANGE_REQUIRED")
    assert client.get(f"{API}/auth/me", headers=headers).status_code == 200  # kendi bilgisi açık

    changed = client.post(
        f"{API}/auth/change-password",
        json={"current_password": "baslangic12", "new_password": "yeniSifre2026"},
        headers=headers,
    )
    assert changed.status_code == 200, changed.text
    assert changed.json()["must_change_password"] is False
    assert client.get(f"{API}/stock", headers=headers).status_code == 200  # aynı oturum sürer
    assert login(client, "depo2", "baslangic12").status_code == 401
    assert login(client, "depo2", "yeniSifre2026").status_code == 200


@pytest.mark.parametrize("password", ["kisa1", "sadeceharf", "12345678"])
def test_weak_passwords_are_rejected(client, admin, password):
    response = new_user(client, admin, password=password)
    assert (response.status_code, response.json()["error"]["code"]) == (422, "VALIDATION_ERROR")


def test_username_rules_and_uniqueness(client, admin):
    assert new_user(client, admin, username="Depo İki").status_code == 422
    assert new_user(client, admin).status_code == 201
    duplicate = new_user(client, admin)
    assert duplicate.status_code == 422
    assert "zaten" in duplicate.json()["error"]["message"]


def test_seller_needs_a_van(client, admin, session):
    no_van = new_user(client, admin, username="satis2", role="SATIS")
    assert no_van.status_code == 422
    van = by_code(session, Warehouse, "ARAC-01")
    assert new_user(client, admin, username="satis2", role="SATIS", warehouse_id=van.id).status_code == 201


def test_reset_password_gives_temporary_password(client, admin):
    user = new_user(client, admin).json()
    response = client.post(f"{API}/users/{user['id']}/reset-password", json={}, headers=admin)
    assert response.status_code == 200, response.text
    temporary = response.json()["temporary_password"]
    assert len(temporary) >= 8
    logged_in = login(client, "depo2", temporary)
    assert logged_in.status_code == 200
    assert logged_in.json()["user"]["must_change_password"] is True


def test_last_admin_cannot_be_removed(client, admin):
    me = client.get(f"{API}/auth/me", headers=admin).json()
    body = {"full_name": me["full_name"], "role": "YONETICI", "active": False}
    response = client.put(f"{API}/users/{me['id']}", json=body, headers=admin)
    assert response.status_code == 422


def test_deactivated_user_cannot_log_in(client, admin):
    user = new_user(client, admin).json()
    body = {"full_name": user["full_name"], "role": "DEPO", "active": False}
    assert client.put(f"{API}/users/{user['id']}", json=body, headers=admin).status_code == 200
    assert login(client, "depo2", "baslangic12").status_code == 401


def test_repeated_wrong_passwords_are_throttled(client):
    for _ in range(10):
        assert login(client, "yonetici", "yanlis-sifre1").status_code == 401
    throttled = login(client, "yonetici", "yonetici123")  # doğru şifre de bir süre beklemeli
    assert (throttled.status_code, throttled.json()["error"]["code"]) == (429, "TOO_MANY_ATTEMPTS")


@pytest.mark.parametrize(
    ("username", "password", "method", "path", "allowed"),
    [
        ("depo1", "depo1234", "get", "/users", False),
        ("depo1", "depo1234", "post", "/recalls", False),
        ("kalite1", "kalite123", "post", "/purchases", False),
        ("magaza1", "magaza123", "post", "/production-orders", False),
        ("uretim1", "uretim123", "post", "/sales", False),
        ("magaza1", "magaza123", "post", "/adjustments", False),
        ("satis1", "satis123", "get", "/stock", False),  # satış elemanı web'e giremez
        ("depo1", "depo1234", "get", "/stock", True),
        ("kalite1", "kalite123", "get", "/trace/forward/ET-2026-001", True),
        ("magaza1", "magaza123", "get", "/day-end", True),
        ("depo1", "depo1234", "get", "/day-end", False),
    ],
)
def test_role_permissions(client, username, password, method, path, allowed):
    headers = auth_header(client, username, password)
    response = getattr(client, method)(
        f"{API}{path}", headers=headers, **({"json": {}} if method == "post" else {})
    )
    if allowed:
        assert response.status_code == 200, response.text
    else:
        assert response.status_code == 403, response.text
