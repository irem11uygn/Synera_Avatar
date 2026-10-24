"""Giriş ve oturum (NFR-007, api.md — Kimlik)."""

from datetime import timedelta

from sqlalchemy import select

from app.models import AuthSession
from app.models.types import utcnow
from tests.helpers import auth_header


def test_sales_user_logs_in_and_gets_van_warehouse(client):
    response = client.post("/api/v1/auth/login", json={"username": "satis1", "password": "satis123"})
    body = response.json()
    assert response.status_code == 200
    assert len(body["token"]) >= 40
    assert body["user"]["role"] == "SATIS"
    assert body["user"]["warehouse_code"] == "ARAC-01"


def test_token_is_stored_only_as_a_digest(client, session):
    response = client.post("/api/v1/auth/login", json={"username": "satis1", "password": "satis123"})
    token = response.json()["token"]
    stored = session.scalars(select(AuthSession.token_hash)).all()
    assert token not in stored and all(len(digest) == 64 for digest in stored)


def test_wrong_password_is_rejected_with_turkish_message(client):
    response = client.post("/api/v1/auth/login", json={"username": "satis1", "password": "yanlis"})
    assert response.status_code == 401
    assert response.json()["error"] == {
        "code": "UNAUTHORIZED",
        "message": "Kullanıcı adı veya parola hatalı.",
        "details": {},
    }


def test_me_returns_logged_in_user(client):
    response = client.get("/api/v1/auth/me", headers=auth_header(client, "yonetici", "yonetici123"))
    assert response.status_code == 200
    assert (response.json()["username"], response.json()["warehouse_id"]) == ("yonetici", None)


def test_missing_or_unknown_token_is_rejected(client):
    assert client.get("/api/v1/auth/me").status_code == 401
    assert client.get("/api/v1/auth/me", headers={"Authorization": "Bearer uydurma"}).status_code == 401


def test_expired_session_is_rejected(client, session):
    headers = auth_header(client, "satis1", "satis123")
    for auth_session in session.scalars(select(AuthSession)):
        auth_session.expires_at = utcnow() - timedelta(seconds=1)
    session.flush()
    assert client.get("/api/v1/auth/me", headers=headers).status_code == 401
