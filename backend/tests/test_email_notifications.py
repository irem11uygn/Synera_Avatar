"""E-posta bildirimleri: mailer, rapor e-postası (yetki, alıcı, sınır, ek), alarm abonelikleri, tekilleştirme.

SMTP hiçbir testte gerçekten açılmaz: mailer'ın bağlantısı sahte nesneyle değiştirilir.
"""

import logging
import smtplib
from dataclasses import replace

import pytest
from sqlalchemy import select

from app import mailer
from app.config import SmtpSettings, get_settings
from app.domain.clock import business_today
from app.mailer import Attachment
from app.models import Alert, AuditEvent, MailMessage, Partner, Product, User, Warehouse
from app.models.enums import AlertKind, LotStatus
from app.services import alarms, mail
from tests.helpers import auth_header, by_code
from tests.helpers import make_lot as stocked_lot

API = "/api/v1"
SMTP = SmtpSettings("smtp.test", 1025, None, None, "AVATAR Synera <avatar@synera.example>", 30)


class FakeSmtp:
    """smtplib.SMTP yerine: gönderilen iletileri ve STARTTLS/giriş çağrılarını kaydeder."""

    instances: list["FakeSmtp"] = []

    def __init__(
        self, host: str = "", port: int = 0, timeout: float = 0, fail: Exception | None = None
    ) -> None:
        self.host, self.port = host, port
        self.sent: list = []
        self.calls: list[str] = []
        self.fail = fail
        FakeSmtp.instances.append(self)

    def starttls(self, context=None) -> None:
        self.calls.append("starttls")

    def login(self, user: str, password: str) -> None:
        self.calls.append(f"login:{user}")

    def send_message(self, message) -> None:
        if self.fail:
            raise self.fail
        self.sent.append(message)

    def quit(self) -> None:
        self.calls.append("quit")


@pytest.fixture
def admin(client):
    return auth_header(client, "yonetici", "yonetici123")


@pytest.fixture
def no_real_smtp(monkeypatch):
    """İstek sırasında SMTP'ye bağlanılırsa test düşer: gönderim arka planda olmalı."""

    def forbidden(_settings):
        raise AssertionError("istek SMTP'yi beklememeli")

    monkeypatch.setattr(mailer, "connect", forbidden)


def by_username(session, username: str) -> User:
    return session.scalars(select(User).where(User.username == username)).one()


def _outbox(session) -> list[MailMessage]:
    return list(session.scalars(select(MailMessage).order_by(MailMessage.id)))


# --- Mailer -------------------------------------------------------------------------------------


def test_send_mail_builds_html_text_and_attachment():
    fake = FakeSmtp()
    result = mailer.send_mail(
        ["a@example.com"],
        "Konu ş",
        "<p>Merhaba <b>dünya</b></p><ul><li>bir</li></ul>",
        Attachment("rapor.csv", b"a;b\r\n1;2\r\n", "text/csv"),
        settings=SMTP,
        transport=lambda _s: fake,
    )
    assert result.ok and result.recipients == ["a@example.com"] and result.error is None
    [message] = fake.sent
    assert message["Subject"] == "Konu ş" and message["From"] == "AVATAR Synera <avatar@synera.example>"
    parts = [part.get_content_type() for part in message.walk()]
    assert parts == ["multipart/mixed", "multipart/alternative", "text/plain", "text/html", "text/csv"]
    plain = next(p for p in message.walk() if p.get_content_type() == "text/plain").get_content()
    assert "Merhaba dünya" in plain and "• bir" in plain
    attachment = next(message.iter_attachments())
    assert attachment.get_filename() == "rapor.csv" and attachment.get_content() == "a;b\r\n1;2\r\n"


def test_starttls_and_login_only_when_user_is_set(monkeypatch):
    monkeypatch.setattr(smtplib, "SMTP", FakeSmtp)
    FakeSmtp.instances.clear()
    mailer.send_mail("a@example.com", "x", "<p>x</p>", settings=SMTP)  # Mailpit: kimlik doğrulamasız
    assert FakeSmtp.instances[-1].calls == ["quit"]
    mailer.send_mail(
        "a@example.com", "x", "<p>x</p>", settings=replace(SMTP, username="u", password="p", port=587)
    )
    assert FakeSmtp.instances[-1].calls == ["starttls", "login:u", "quit"]


def test_smtp_error_is_logged_and_returned_not_raised(caplog, monkeypatch):
    # Test oturumunda Alembic'in logging.fileConfig'i önceden oluşmuş günlükçüleri kapatır; burada aç.
    monkeypatch.setattr(logging.getLogger("app.mailer"), "disabled", False)
    caplog.set_level(logging.WARNING, logger="app.mailer")
    fake = FakeSmtp(fail=smtplib.SMTPRecipientsRefused({"a@example.com": (550, b"yok")}))
    result = mailer.send_mail("a@example.com", "x", "<p>x</p>", settings=SMTP, transport=lambda _s: fake)
    assert not result.ok and "SMTPRecipientsRefused" in result.error
    assert "E-posta gönderilemedi" in caplog.text

    def unreachable(_s):
        raise ConnectionRefusedError("bağlantı reddedildi")

    result = mailer.send_mail("a@example.com", "x", "<p>x</p>", settings=SMTP, transport=unreachable)
    assert not result.ok and "ConnectionRefusedError" in result.error


# --- Rapor e-postası ----------------------------------------------------------------------------


def _email(client, headers, recipients, code="sales", note=None, query=None):
    return client.post(
        f"{API}/reports/{code}/email",
        json={"recipients": recipients, "note": note},
        headers=headers,
        params=query,
    )


def test_report_email_requires_login_and_report_permission(client, session):
    assert _email(client, {}, ["yonetici@synera.example"]).status_code == 401
    seller = auth_header(client, "satis1", "satis123")  # yalnız telefon: raporları göremez
    response = _email(client, seller, ["yonetici@synera.example"])
    assert response.status_code == 403 and response.json()["error"]["code"] == "FORBIDDEN"
    assert _outbox(session) == []


def test_report_email_rejects_unknown_recipients(client, admin, session, monkeypatch):
    rejected = _email(client, admin, ["yonetici@synera.example", "yabanci@kotu.example"])
    assert rejected.status_code == 422
    assert rejected.json()["error"]["details"]["rejected"] == ["yabanci@kotu.example"]
    assert _email(client, admin, ["adres-degil"]).status_code == 422
    assert _email(client, admin, []).status_code == 422
    assert _email(client, admin, [f"k{i}@synera.example" for i in range(21)]).status_code == 422
    # Pasif kullanıcının adresi de izinli değil.
    by_username(session, "depo1").active = False
    session.flush()
    assert _email(client, admin, ["depo@synera.example"]).status_code == 422
    assert _outbox(session) == []
    # İzinli alan adı ayarlanınca (ALLOWED_EMAIL_DOMAINS) sistem dışı adres kabul edilir.
    monkeypatch.setattr(
        "app.services.mail_policy.get_settings",
        lambda: replace(get_settings(), allowed_email_domains=("bayi.example",)),
    )
    assert _email(client, admin, ["satinalma@bayi.example"]).status_code == 202


def test_report_email_is_queued_with_csv_attachment_and_audited(client, admin, session, no_real_smtp):
    response = _email(
        client,
        admin,
        ["kalite@synera.example", "Depo@Synera.example"],
        code="purchases",
        note="<b>Toplantı</b> için",
    )
    assert response.status_code == 202, response.text
    body = response.json()
    assert body["status"] == "KUYRUKTA" and body["attachment"] == "rapor_purchases.csv"
    assert body["subject"] == "[AVATAR] Alış raporu"
    [message] = _outbox(session)
    assert message.kind == "RAPOR" and message.recipients == "kalite@synera.example, Depo@Synera.example"
    assert message.attachment_mime == "text/csv"
    csv = message.attachment.decode("utf-8")
    assert csv.startswith("﻿") and "ET-2026-001" in csv
    assert (
        "&lt;b&gt;Toplantı&lt;/b&gt;" in message.html and "<b>Toplantı</b>" not in message.html
    )  # not kaçışlı
    assert "/raporlar/purchases" in message.html
    event = session.scalars(select(AuditEvent).where(AuditEvent.action == "RAPOR_EPOSTA")).one()
    assert (
        event.username == "yonetici"
        and "kalite@synera.example" in event.message
        and "purchases" in event.message
    )


def test_report_email_rate_limit_is_per_user(client, admin, session):
    for _ in range(5):
        assert _email(client, admin, ["kalite@synera.example"]).status_code == 202
    limited = _email(client, admin, ["kalite@synera.example"])
    assert limited.status_code == 429 and limited.json()["error"]["code"] == "TOO_MANY_ATTEMPTS"
    quality = auth_header(client, "kalite1", "kalite123")
    assert (
        _email(client, quality, ["yonetici@synera.example"]).status_code == 202
    )  # başka kullanıcı etkilenmez
    assert len(_outbox(session)) == 6


def test_queued_report_is_delivered_by_the_outbox(client, admin, session):
    assert _email(client, admin, ["kalite@synera.example"], code="integrity").status_code == 202
    fake = FakeSmtp()
    result = mail.deliver_pending(session, SMTP, transport=lambda _s: fake)
    assert (result.sent, result.failed) == (1, 0)
    [sent] = fake.sent
    assert sent["To"] == "kalite@synera.example"
    assert next(sent.iter_attachments()).get_filename() == "rapor_integrity.csv"
    [message] = _outbox(session)
    assert message.status.value == "GONDERILDI" and message.sent_at is not None and message.attempts == 1


# --- Alarm abonelikleri -------------------------------------------------------------------------


def _subscriptions(client, headers) -> dict[str, bool]:
    body = client.get(f"{API}/alerts/subscriptions", headers=headers).json()
    return {s["alert_type"]: s["enabled"] for s in body["subscriptions"]}


def test_default_subscriptions_follow_role(client, admin):
    assert all(_subscriptions(client, admin).values()) and "HATALI_GIRIS" in _subscriptions(client, admin)
    depot = auth_header(client, "depo1", "depo1234")
    mine = _subscriptions(client, depot)
    assert mine["FIYAT_ARTISI"] and mine["SAYIM_FARKI"] and mine["SKT_YAKLASIYOR"]
    assert not mine["VERIM_SAPMASI"] and not mine["GERI_CAGIRMA"]
    assert "HATALI_GIRIS" not in mine  # yalnız yönetici görür
    production = auth_header(client, "uretim1", "uretim123")
    assert {k for k, v in _subscriptions(client, production).items() if v} == {"VERIM_SAPMASI"}


def test_update_subscriptions(client, session):
    depot = auth_header(client, "depo1", "depo1234")
    body = client.put(
        f"{API}/alerts/subscriptions",
        json={
            "subscriptions": [
                {"alert_type": "FIYAT_ARTISI", "enabled": False},
                {"alert_type": "VERIM_SAPMASI", "enabled": True},
            ]
        },
        headers=depot,
    ).json()
    items = {s["alert_type"]: s for s in body["subscriptions"]}
    assert body["email"] == "depo@synera.example"
    assert items["FIYAT_ARTISI"]["enabled"] is False and items["FIYAT_ARTISI"]["is_default"] is False
    assert items["VERIM_SAPMASI"]["enabled"] is True and items["SAYIM_FARKI"]["is_default"] is True
    assert (
        session.scalars(select(AuditEvent).where(AuditEvent.action == "ABONELIK")).one().username == "depo1"
    )
    refused = client.put(
        f"{API}/alerts/subscriptions",
        json={"subscriptions": [{"alert_type": "HATALI_GIRIS", "enabled": True}]},
        headers=depot,
    )
    assert refused.status_code == 422


def _price_increase(client, session) -> Alert:
    depot = auth_header(client, "depo1", "depo1234")
    body = {
        "supplier_id": by_code(session, Partner, "TED-ET").id,
        "doc_no": "FAT-ET-ABONE",
        "doc_date": business_today().isoformat(),
        "lines": [
            {
                "product_id": by_code(session, Product, "ET").id,
                "lot_no": "ET-ABONE-1",
                "qty": "10",
                "unit_price": "12.00",
            }
        ],
    }
    assert client.post(f"{API}/purchases", json=body, headers=depot).status_code == 201
    return session.scalars(select(Alert).where(Alert.kind == AlertKind.FIYAT_ARTISI)).one()


def test_alert_mail_goes_to_subscribers_only(client, session, no_real_smtp):
    alert = _price_increase(client, session)
    messages = [m for m in _outbox(session) if m.alert_id == alert.id]
    assert {m.recipients for m in messages} == {"yonetici@synera.example", "depo@synera.example"}
    message = messages[0]
    assert message.subject == "[AVATAR UYARI] Alış fiyatı artışı"
    assert (
        "ET-ABONE-1" in message.html and "Sucukluk et" in message.html and "Örnek Et Tedarik" in message.html
    )
    assert f"{get_settings().web_base_url}/alislar" in message.html and "/alarmlar" in message.body


def test_unsubscribed_user_gets_no_alert_mail(client, session):
    depot = auth_header(client, "depo1", "depo1234")
    client.put(
        f"{API}/alerts/subscriptions",
        json={"subscriptions": [{"alert_type": "FIYAT_ARTISI", "enabled": False}]},
        headers=depot,
    )
    alert = _price_increase(client, session)
    assert [m.recipients for m in _outbox(session) if m.alert_id == alert.id] == ["yonetici@synera.example"]


def test_same_alert_is_mailed_once_per_recipient(client, session):
    alert = _price_increase(client, session)
    before = len(_outbox(session))
    assert alarms.notify(session, alert) == []  # ikinci kez: hiçbir alıcıya yeniden gitmez
    assert len(_outbox(session)) == before
    keys = [m.dedup_key for m in _outbox(session) if m.alert_id == alert.id]
    assert sorted(keys) == sorted(
        {f"ALERT:{alert.id}:yonetici@synera.example", f"ALERT:{alert.id}:depo@synera.example"}
    )


# --- Yeni uyarı türleri: sayım farkı, SKT yaklaşan lot -----------------------------------------


def test_stock_count_difference_raises_alert_and_mail(client, session):
    stocked_lot(session, "SAY-LOT-1", product="ET", qty="10", value="97.00", days_left=20)
    depot = auth_header(client, "depo1", "depo1234")
    response = client.post(
        f"{API}/stock-counts",
        json={
            "warehouse_id": by_code(session, Warehouse, "ANA").id,
            "lines": [{"lot_no": "SAY-LOT-1", "counted_qty": "9.5"}],
        },
        headers=depot,
    )
    assert response.status_code == 201, response.text
    [alert] = session.scalars(select(Alert).where(Alert.kind == AlertKind.SAYIM_FARKI)).all()
    assert "SAY-LOT-1" in alert.message and "-0,5 kg" in alert.message
    recipients = {m.recipients for m in _outbox(session) if m.alert_id == alert.id}
    assert recipients == {"yonetici@synera.example", "depo@synera.example"}
    message = next(m for m in _outbox(session) if m.alert_id == alert.id)
    assert message.subject == "[AVATAR UYARI] Sayım farkı" and "/sayim" in message.html


def test_expiring_lot_alert_on_rule_run(client, admin, session):
    lot = stocked_lot(session, "SKT-LOT-1", product="NARIN-SUCUK", qty="12", value="200.00", days_left=2)
    blocked = stocked_lot(session, "SKT-LOT-2", product="NARIN-SUCUK", qty="5", value="80.00", days_left=1)
    blocked.status = LotStatus.BLOKE
    session.flush()
    run = client.post(f"{API}/alerts/run-rules", headers=admin).json()
    created = {a["ref_id"]: a for a in run["created"] if a["kind"] == "SKT_YAKLASIYOR"}
    assert lot.id in created and blocked.id not in created  # bloke lot "bloke stok" alarmının işi
    assert "2 gün sonra" in created[lot.id]["message"]
    alert_id = created[lot.id]["id"]
    message = next(
        m for m in _outbox(session) if m.alert_id == alert_id and m.recipients == "magaza@synera.example"
    )
    assert "/lotlar/SKT-LOT-1" in message.html and "Narin Sucuk" in message.html
    again = client.post(f"{API}/alerts/run-rules", headers=admin).json()
    assert [a for a in again["created"] if a["kind"] == "SKT_YAKLASIYOR"] == []


# --- Serbest e-posta (POST /mail): açık röle yok, ortak sınır ---------------------------------------


def _mail(client, headers, recipients, subject="Not"):
    return client.post(
        f"{API}/mail", json={"recipients": recipients, "subject": subject, "body": "Metin"}, headers=headers
    )


def test_mail_endpoint_accepts_only_known_or_allowed_addresses(client, session, monkeypatch):
    store = auth_header(client, "magaza1", "magaza123")
    refused = _mail(client, store, ["yabanci@kotu.example", "market-a@example.com"])
    assert refused.status_code == 422 and refused.json()["error"]["details"]["rejected"] == [
        "yabanci@kotu.example"
    ]
    assert "kayıtlı bir cari" in refused.json()["error"]["message"]
    assert (
        _mail(
            client, store, ["market-a@example.com", "et-tedarik@example.com", "yonetici@synera.example"]
        ).status_code
        == 201
    )
    by_username(session, "depo1").active = False
    session.flush()
    assert _mail(client, store, ["depo@synera.example"]).status_code == 422  # pasif kullanıcı
    monkeypatch.setattr(
        "app.services.mail_policy.get_settings",
        lambda: replace(get_settings(), allowed_email_domains=("bayi.example",)),
    )
    assert _mail(client, store, ["satinalma@bayi.example"]).status_code == 201
    assert [m.recipients for m in _outbox(session)] == [
        "market-a@example.com, et-tedarik@example.com, yonetici@synera.example",
        "satinalma@bayi.example",
    ]


def test_report_email_does_not_accept_partner_addresses(client, admin):
    # Rapor (iç veri) yalnız kullanıcılara ya da izinli alan adlarına; cariye değil.
    response = _email(client, admin, ["market-a@example.com"])
    assert response.status_code == 422 and response.json()["error"]["details"]["rejected"] == [
        "market-a@example.com"
    ]


def test_mail_and_report_email_share_the_per_user_limit(client, admin):
    for _ in range(3):
        assert _email(client, admin, ["kalite@synera.example"]).status_code == 202
    for _ in range(2):
        assert _mail(client, admin, ["kalite@synera.example"]).status_code == 201
    limited = _mail(client, admin, ["kalite@synera.example"])
    assert limited.status_code == 429 and limited.json()["error"]["code"] == "TOO_MANY_ATTEMPTS"
    assert _email(client, admin, ["kalite@synera.example"]).status_code == 429


def test_mail_batch_is_one_send_and_all_or_nothing(client, admin, session):
    customers = [
        "market-a@example.com",
        "market-b@example.com",
        "market-c@example.com",
        "market-b-sube1@example.com",
        "market-b-sube2@example.com",
        "kalite@synera.example",
    ]
    messages = [
        {"recipients": [address], "subject": "Geri çağırma", "body": f"Size: {address}"}
        for address in customers
    ]
    response = client.post(f"{API}/mail/batch", json={"messages": messages}, headers=admin)
    assert response.status_code == 201 and [m["recipients"] for m in response.json()] == customers
    assert len(_outbox(session)) == 6  # her alıcıya ayrı e-posta, tek gönderim sayıldı:
    for _ in range(4):
        assert _mail(client, admin, ["kalite@synera.example"]).status_code == 201
    assert _mail(client, admin, ["kalite@synera.example"]).status_code == 429

    other = auth_header(client, "kalite1", "kalite123")
    bad = [*messages[:2], {"recipients": ["yabanci@kotu.example"], "subject": "x", "body": "y"}]
    refused = client.post(f"{API}/mail/batch", json={"messages": bad}, headers=other)
    assert refused.status_code == 422
    assert len(_outbox(session)) == 10  # 6 + 4; reddedilen toplu gönderimden hiçbiri yazılmadı
