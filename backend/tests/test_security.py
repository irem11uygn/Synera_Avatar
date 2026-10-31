"""Güvenlik testleri: şifre özeti; denetimde eklenenler: CORS, önbellek, hata sızıntısı, enjeksiyon, girdi
doğrulama, e-posta başlığı, ilk kurulum şifreleri ve ilk yönetici komutu."""

import re

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import create_admin, mailer
from app.main import create_app
from app.models import MailMessage, Partner, Product, User, Warehouse
from app.security import hash_password, verify_password
from app.seed import _load_users
from tests.helpers import auth_header, by_code

API = "/api/v1"


def test_password_round_trip():
    stored = hash_password("gizli-parola")
    assert verify_password("gizli-parola", stored)
    assert not verify_password("baska-parola", stored)


def test_same_password_gets_different_salt():
    assert hash_password("ayni") != hash_password("ayni")


def test_malformed_hash_is_rejected():
    assert not verify_password("x", "bozuk-ozet")


def test_cross_origin_requests_get_no_cors_permission(client):
    """CORS ara katmanı yok: başka siteden gelen tarayıcı isteği yanıtı okuyamaz (web aynı adresten)."""
    preflight = client.options(
        f"{API}/auth/login",
        headers={"Origin": "https://kotu.example", "Access-Control-Request-Method": "POST"},
    )
    assert "access-control-allow-origin" not in {k.lower() for k in preflight.headers}
    response = client.get(f"{API}/health", headers={"Origin": "https://kotu.example"})
    assert "access-control-allow-origin" not in {k.lower() for k in response.headers}


def test_api_responses_are_not_cached(client):
    assert client.get(f"{API}/health").headers["cache-control"] == "no-store"
    admin = auth_header(client, "yonetici", "yonetici123")
    assert (
        client.get(f"{API}/reports/sales", params={"format": "csv"}, headers=admin).headers["cache-control"]
        == "no-store"
    )


def test_unexpected_error_reveals_no_internal_detail():
    app = create_app()

    @app.get(f"{API}/patlat")
    def explode() -> None:
        raise RuntimeError("gizli-ic-ayrinti SELECT * FROM users")

    response = TestClient(app, raise_server_exceptions=False).get(f"{API}/patlat")
    assert response.status_code == 500 and response.json()["error"]["code"] == "INTERNAL_ERROR"
    assert "gizli" not in response.text and "SELECT" not in response.text and "Traceback" not in response.text


def test_sql_injection_payloads_are_plain_text(client):
    admin = auth_header(client, "yonetici", "yonetici123")
    payload = "' OR '1'='1"
    lots = client.get(f"{API}/lots", params={"q": payload}, headers=admin)
    assert lots.status_code == 200 and lots.json() == []  # bütün lotlar dönmedi
    trace = client.get(f"{API}/trace/forward/{payload}", headers=admin)
    assert trace.status_code == 404 and trace.json()["error"]["code"] == "NOT_FOUND"
    audit = client.get(f"{API}/audit", params={"q": "x'; DROP TABLE users; --"}, headers=admin)
    assert audit.status_code == 200 and audit.json() == []
    assert client.get(f"{API}/auth/me", headers=admin).status_code == 200  # tablo yerinde


def test_server_side_validation_rejects_bad_input(client, session):
    admin = auth_header(client, "yonetici", "yonetici123")
    purchase = {
        "supplier_id": by_code(session, Partner, "TED-ET").id,
        "doc_no": "FAT-NEG",
        "doc_date": "2026-10-28",
        "lines": [
            {
                "product_id": by_code(session, Product, "ET").id,
                "lot_no": "NEG-1",
                "qty": "-5",
                "unit_price": "9",
            }
        ],
    }
    assert client.post(f"{API}/purchases", json=purchase, headers=admin).status_code == 422
    assert (
        client.post(
            f"{API}/recalls", json={"lot_no": "ET-2026-001", "reason": "x" * 501}, headers=admin
        ).status_code
        == 422
    )
    bad_role = {"username": "kotu.rol", "full_name": "X", "role": "SUPERADMIN", "password": "abc12345"}
    assert client.post(f"{API}/users", json=bad_role, headers=admin).status_code == 422
    count = {
        "warehouse_id": by_code(session, Warehouse, "ANA").id,
        "lines": [{"lot_no": "ET-2026-001", "counted_qty": "-1"}],
    }
    assert client.post(f"{API}/stock-counts", json=count, headers=admin).status_code == 422


def test_stored_markup_is_returned_as_text_and_escaped_in_mail(client, session):
    admin = auth_header(client, "yonetici", "yonetici123")
    partner = client.post(
        f"{API}/partners",
        json={
            "code": "XSS-1",
            "name": "<script>alert(1)</script>",
            "is_customer": True,
            "email": "xss@example.com",
        },
        headers=admin,
    ).json()
    assert partner["name"] == "<script>alert(1)</script>"  # olduğu gibi metin; web arayüzü kaçışlı gösterir
    html = mailer.text_to_html("<script>alert(1)</script>")
    assert "<script>" not in html and "&lt;script&gt;" in html


def test_mail_header_injection_is_neutralised(client, session):
    store = auth_header(client, "magaza1", "magaza123")
    response = client.post(
        f"{API}/mail",
        json={
            "recipients": ["yonetici@synera.example"],
            "subject": "Konu\r\nBcc: saldirgan@kotu.example",
            "body": "x",
        },
        headers=store,
    )
    assert response.status_code == 201
    message = session.get(MailMessage, response.json()["id"])
    assert "\n" not in message.subject and "\r" not in message.subject
    mime = mailer.build_message("a@b.example", message.recipients.split(", "), message.subject, "<p>x</p>")
    assert mime["Bcc"] is None and mime["To"] == "yonetici@synera.example"
    injected = client.post(
        f"{API}/mail",
        json={
            "recipients": ["yonetici@synera.example\r\nBcc: saldirgan@kotu.example"],
            "subject": "x",
            "body": "x",
        },
        headers=store,
    )
    assert injected.status_code == 422


def test_seed_users_get_temporary_passwords_outside_demo(client, session):
    _load_users(
        session,
        [{"username": "gecici.depo", "full_name": "Geçici", "role": "DEPO", "password": "bilinen123"}],
        {},
        True,
    )
    session.flush()
    user = session.scalars(select(User).where(User.username == "gecici.depo")).one()
    assert user.must_change_password is True
    headers = auth_header(client, "gecici.depo", "bilinen123")
    blocked = client.get(f"{API}/stock", headers=headers)
    assert blocked.status_code == 403 and blocked.json()["error"]["code"] == "PASSWORD_CHANGE_REQUIRED"


def test_create_admin_command_prints_one_time_password(client, session, monkeypatch, capsys):
    monkeypatch.setattr(
        create_admin,
        "get_sessionmaker",
        lambda: lambda: Session(bind=session.connection(), join_transaction_mode="create_savepoint"),
    )
    assert create_admin.main(["ilk.yonetici", "İlk Yönetici", "ilk@synera.example"]) == 0
    output = capsys.readouterr().out
    password = re.search(r"Geçici şifre \(bir kez gösterilir\): (\S+)", output).group(1)
    user = session.scalars(select(User).where(User.username == "ilk.yonetici")).one()
    assert user.role.value == "YONETICI" and user.must_change_password and user.email == "ilk@synera.example"
    headers = auth_header(client, "ilk.yonetici", password)
    assert client.get(f"{API}/users", headers=headers).json()["error"]["code"] == "PASSWORD_CHANGE_REQUIRED"
    assert create_admin.main(["ilk.yonetici", "İkinci"]) == 1  # aynı ad: hiçbir şey değişmez
    assert create_admin.main([]) == 2
