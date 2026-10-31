"""Alarm merkezi, kural motoru, denetim günlüğü, e-posta giden kutusu, fatura metni ve hesaplayıcılar."""

import smtplib
from dataclasses import replace
from decimal import Decimal as D

import pytest
from sqlalchemy import func, select

from app.config import SmtpSettings, get_settings
from app.demo import build_demo_scenario
from app.domain.clock import business_today
from app.models import (
    AiForecast,
    Alert,
    AuditEvent,
    Lot,
    MailMessage,
    Partner,
    Product,
    ProductionOrder,
    Sale,
)
from app.models.enums import AlertKind, ForecastTarget, LotStatus, MailStatus, Severity
from app.services import alarms, mail
from app.services.invoice_text import parse_invoice_text, parse_number
from tests.helpers import auth_header, by_code, store_sale
from tests.helpers import make_lot as stocked_lot

API = "/api/v1"


@pytest.fixture
def admin(client):
    return auth_header(client, "yonetici", "yonetici123")


def _alerts(session, kind: AlertKind) -> list[Alert]:
    return list(session.scalars(select(Alert).where(Alert.kind == kind)))


def _mails(session) -> list[MailMessage]:
    return list(session.scalars(select(MailMessage).order_by(MailMessage.id)))


# --- Hatalı giriş ---


def test_three_failed_logins_raise_one_critical_alarm_and_mail(client, session):
    for _ in range(3):
        response = client.post(f"{API}/auth/login", json={"username": "kalite1", "password": "yanlis"})
        assert response.status_code == 401 and response.json()["error"]["code"] == "UNAUTHORIZED"
    events = session.scalars(select(AuditEvent).where(AuditEvent.action == "GIRIS_HATASI")).all()
    assert len(events) == 3 and all(e.username == "kalite1" for e in events)
    [alert] = _alerts(session, AlertKind.HATALI_GIRIS)
    assert alert.severity == Severity.KRITIK and "kalite1" in alert.message
    # Hatalı giriş alarmı yalnız yöneticiye görünür; e-postası da yalnız yöneticiye (abonelik varsayılanı).
    [message] = [m for m in _mails(session) if m.alert_id == alert.id]
    assert message.status == MailStatus.KUYRUKTA
    assert message.recipients == "yonetici@synera.example"
    assert message.subject == "[AVATAR UYARI] Art arda hatalı giriş"

    client.post(f"{API}/auth/login", json={"username": "kalite1", "password": "yanlis"})
    assert len(_alerts(session, AlertKind.HATALI_GIRIS)) == 1  # 4. deneme yeni alarm açmaz

    auth_header(client, "kalite1", "kalite123")  # başarılı giriş sayacı sıfırlar
    for _ in range(3):
        client.post(f"{API}/auth/login", json={"username": "kalite1", "password": "yanlis"})
    assert len(_alerts(session, AlertKind.HATALI_GIRIS)) == 2


def test_failed_login_alarm_visible_only_to_admin(client, session, admin):
    for _ in range(3):
        client.post(f"{API}/auth/login", json={"username": "olmayan", "password": "x"})
    quality = auth_header(client, "kalite1", "kalite123")
    kinds = {a["kind"] for a in client.get(f"{API}/alerts", headers=quality).json()}
    assert "HATALI_GIRIS" not in kinds
    assert client.get(f"{API}/alerts/summary", headers=quality).json()["open_critical"] == 0
    summary = client.get(f"{API}/alerts/summary", headers=admin).json()
    assert summary["open_critical"] == 1 and summary["latest"][0]["kind"] == "HATALI_GIRIS"
    assert "Bu adla bir kullanıcı yok" in summary["latest"][0]["message"]


# --- Denetim günlüğü ---


def test_audit_log_records_who_did_what_and_exports_csv(client, admin, session):
    client.post(f"{API}/auth/login", json={"username": "yonetici", "password": "yanlis"})
    rows = client.get(f"{API}/audit", headers=admin).json()
    actions = [r["action"] for r in rows]
    assert "GIRIS" in actions and "GIRIS_HATASI" in actions
    login = next(r for r in rows if r["action"] == "GIRIS")
    assert login["username"] == "yonetici" and login["full_name"] == "Demo Yönetici"

    warnings = client.get(f"{API}/audit", params={"severity": "UYARI"}, headers=admin).json()
    assert {r["action"] for r in warnings} == {"GIRIS_HATASI"}
    assert (
        client.get(f"{API}/audit", params={"q": "hatalı"}, headers=admin).json()[0]["action"]
        == "GIRIS_HATASI"
    )

    csv = client.get(f"{API}/audit/export.csv", headers=admin)
    assert csv.status_code == 200 and "Zaman (yerel);Kullanıcı" in csv.content.decode("utf-8-sig")

    store = auth_header(client, "magaza1", "magaza123")
    assert client.get(f"{API}/audit", headers=store).status_code == 403


# --- Bloke lot satış denemesi ---


def test_blocked_lot_store_sale_is_rejected_and_raises_alarm(client, admin, session):
    lot = stocked_lot(session, "BLK-1", product="ET", qty="10", value="97.00")
    lot.status = LotStatus.BLOKE
    session.flush()
    sales_before = session.scalar(select(func.count()).select_from(Sale))

    store = auth_header(client, "magaza1", "magaza123")
    response = store_sale(client, store, session, {"lot_no": "BLK-1", "qty": "1", "unit_price": "12.00"})
    assert response.status_code == 409 and response.json()["error"]["code"] == "LOT_BLOCKED"
    assert session.scalar(select(func.count()).select_from(Sale)) == sales_before  # yarım satış kalmadı
    [alert] = _alerts(session, AlertKind.BLOKE_SATIS_DENEMESI)
    assert alert.severity == Severity.KRITIK and "BLK-1" in alert.message and "magaza1" in alert.message
    assert session.scalars(select(AuditEvent).where(AuditEvent.action == "ALARM")).first() is not None
    # Mağaza kasası bu alarmı okundu işaretleyebilir; depo işaretleyemez.
    depot = auth_header(client, "depo1", "depo1234")
    assert client.post(f"{API}/alerts/{alert.id}/ack", headers=depot).status_code == 403
    acked = client.post(f"{API}/alerts/{alert.id}/ack", headers=store).json()
    assert acked["acknowledged_by_name"] == "Demo Mağaza Kasası"


# --- Geri çağırma ---


def test_recall_start_raises_critical_alarm_and_mail(client, admin, session):
    build_demo_scenario(session)
    started = client.post(f"{API}/recalls", json={"lot_no": "ET-2026-001", "reason": "Test"}, headers=admin)
    assert started.status_code == 201
    [alert] = _alerts(session, AlertKind.GERI_CAGIRMA)
    assert alert.severity == Severity.KRITIK and "ET-2026-001" in alert.message
    # Her aboneye ayrı e-posta: yönetici (bütün türler) ve kalite (geri çağırma varsayılanı).
    messages = [m for m in _mails(session) if m.alert_id == alert.id]
    assert {m.recipients for m in messages} == {"yonetici@synera.example", "kalite@synera.example"}
    assert all(m.subject == "[AVATAR UYARI] Geri çağırma başlatıldı" for m in messages)


# --- Fiyat artışı kuralı ve eşikler ---


def _purchase(client, headers, session, lot_no, price):
    body = {
        "supplier_id": by_code(session, Partner, "TED-ET").id,
        "doc_no": f"FAT-{lot_no}",
        "doc_date": business_today().isoformat(),
        "lines": [
            {
                "product_id": by_code(session, Product, "ET").id,
                "lot_no": lot_no,
                "qty": "10",
                "unit_price": price,
            }
        ],
    }
    response = client.post(f"{API}/purchases", json=body, headers=headers)
    assert response.status_code == 201, response.text


def test_price_increase_rule_uses_editable_threshold(client, admin, session):
    _purchase(client, admin, session, "ET-T-1", "11.00")  # önceki 9,70 → %13,4 artış (eşik %10)
    [alert] = _alerts(session, AlertKind.FIYAT_ARTISI)
    assert alert.severity == Severity.UYARI and "%13,4" in alert.message
    assert client.post(f"{API}/alerts/run-rules", headers=admin).json()["created"] == []  # tekrar açılmaz

    assert (
        client.put(
            f"{API}/settings/alarm-thresholds", json={"price_increase_pct": "abc"}, headers=admin
        ).status_code
        == 422
    )
    assert (
        client.put(
            f"{API}/settings/alarm-thresholds", json={"price_increase_pct": "900"}, headers=admin
        ).status_code
        == 422
    )
    quality = auth_header(client, "kalite1", "kalite123")
    assert (
        client.put(f"{API}/settings/alarm-thresholds", json={"yield_z": "3"}, headers=quality).status_code
        == 403
    )
    saved = client.put(
        f"{API}/settings/alarm-thresholds", json={"price_increase_pct": "25"}, headers=admin
    ).json()
    assert saved["price_increase_pct"] == "25" and saved["yield_z"] == "2.0"
    assert (
        session.scalars(select(AuditEvent).where(AuditEvent.action == "AYAR")).one().severity
        == Severity.UYARI
    )

    _purchase(client, admin, session, "ET-T-2", "13.00")  # 11,00 → 13,00: %18,2 < %25
    assert len(_alerts(session, AlertKind.FIYAT_ARTISI)) == 1


# --- Verim sapması (z-skoru) ---


def test_yield_deviation_alarm_from_model_forecast(client, admin, session):
    build_demo_scenario(session)
    order = session.scalars(select(ProductionOrder).where(ProductionOrder.order_no == "URT-2026-045")).one()
    forecast = session.scalars(
        select(AiForecast).where(
            AiForecast.target_type == ForecastTarget.URETIM_EMRI, AiForecast.target_id == order.id
        )
    ).one()
    forecast.prediction = {**forecast.prediction, "yield_main_pct": "75.00"}  # gerçek %85: çok yüksek
    session.flush()
    run = client.post(f"{API}/alerts/run-rules", headers=admin).json()
    [created] = [a for a in run["created"] if a["kind"] == "VERIM_SAPMASI"]
    assert "URT-2026-045" in created["message"] and "yüksek" in created["message"]
    again = client.post(f"{API}/alerts/run-rules", headers=admin).json()
    assert [a for a in again["created"] if a["kind"] == "VERIM_SAPMASI"] == []


def test_demo_scenario_alone_raises_no_rule_alarm(client, admin, session):
    build_demo_scenario(session)
    run = client.post(f"{API}/alerts/run-rules", headers=admin).json()
    # Kural alarmı yok; yalnız SKT'si 3 gün içinde dolan parça lotu olabilir (tarih kurulum gününe göre).
    assert {a["kind"] for a in run["created"]} <= {"SKT_YAKLASIYOR"}, run


# --- E-posta ---


def test_report_mail_is_queued_and_outbox_is_scoped(client, admin, session, monkeypatch):
    store = auth_header(client, "magaza1", "magaza123")
    recipients = client.get(f"{API}/mail/recipients", headers=store).json()
    assert {
        "name": "Market A",
        "email": "market-a@example.com",
        "group": "Müşteri",
        "role": None,
    } in recipients
    bad = client.post(
        f"{API}/mail", json={"recipients": ["yanlis"], "subject": "x", "body": "y"}, headers=store
    )
    assert bad.status_code == 422
    sent = client.post(
        f"{API}/mail",
        json={
            "recipients": ["market-a@example.com; yonetici@synera.example"],
            "subject": "Gün sonu",
            "body": "Rapor",
        },
        headers=store,
    ).json()
    assert (
        sent["status"] == "KUYRUKTA" and sent["recipients"] == "market-a@example.com, yonetici@synera.example"
    )
    assert sent["body"].startswith("Rapor") and "Synera" in sent["body"]
    assert [m["id"] for m in client.get(f"{API}/mail/outbox", headers=store).json()] == [sent["id"]]
    assert sent["id"] in [m["id"] for m in client.get(f"{API}/mail/outbox", headers=admin).json()]
    assert client.get(f"{API}/mail/status", headers=store).json()["host"] == "mailpit"  # varsayılan
    # E-posta kapalıyken (SMTP_HOST boş): durum "tanımlı değil", elle gönderme reddedilir.
    monkeypatch.setattr("app.api.mail.get_settings", lambda: replace(get_settings(), smtp=None))
    status = client.get(f"{API}/mail/status", headers=store).json()
    assert status["smtp_configured"] is False
    assert client.post(f"{API}/mail/deliver", headers=admin).json()["error"]["code"] == "INVALID_STATE"


class _FakeSmtp:
    def __init__(self, fail_for: str | None = None) -> None:
        self.sent: list[str] = []
        self.fail_for = fail_for

    def send_message(self, message) -> None:
        if self.fail_for and self.fail_for in message["To"]:
            raise smtplib.SMTPRecipientsRefused({message["To"]: (550, b"no")})
        self.sent.append(message["Subject"])

    def quit(self) -> None:
        pass


def test_deliver_pending_marks_sent_and_failed(session):
    settings = SmtpSettings("smtp.test", 587, None, None, "synera@test", 30)
    mail.queue(session, recipients=["a@example.com"], subject="Bir", body="1", kind="RAPOR")
    mail.queue(session, recipients=["red@example.com"], subject="İki", body="2", kind="RAPOR")
    fake = _FakeSmtp(fail_for="red@")
    result = mail.deliver_pending(session, settings, transport=lambda _s: fake)
    assert (result.sent, result.failed) == (1, 1) and fake.sent == ["Bir"]
    first, second = _mails(session)
    assert first.status == MailStatus.GONDERILDI and first.sent_at is not None
    assert (
        second.status == MailStatus.HATA
        and second.attempts == 1
        and "SMTPRecipientsRefused" in second.last_error
    )

    def unreachable(_s):
        raise OSError("bağlantı yok")

    assert mail.deliver_pending(session, settings, transport=unreachable).failed == 1
    assert second.attempts == 2


# --- Fatura metninden öneri ---


INVOICE = """Örnek Et Tedarik — TED-ET
e-Fatura No: FAT-ET-2026-0420
Fatura Tarihi: 27.10.2026
1  Sucukluk et   LOT: ET-2026-002   120 kg x 9,90 € = 1.188,00 €
   SKT: 15.11.2026
2  Doğal bağırsak   6 kg   11,60 €/kg   Tutar: 70,00
"""


def test_parse_invoice_text_suggests_receipt_lines(client, session):
    depot = auth_header(client, "depo1", "depo1234")
    body = client.post(f"{API}/purchases/parse-text", json={"text": INVOICE}, headers=depot).json()
    assert body["supplier_name"] == "Örnek Et Tedarik" and body["doc_no"] == "FAT-ET-2026-0420"
    assert body["doc_date"] == "2026-10-27"
    meat, casing = body["lines"]
    assert (meat["product_code"], D(meat["qty"]), D(meat["unit_price"]), meat["lot_no"]) == (
        "ET",
        D(120),
        D("9.90"),
        "ET-2026-002",
    )
    assert D(meat["invoice_amount"]) == D("1188.00") and meat["expiry_date"] == "2026-11-15"
    assert meat["warnings"] == [] and meat["match"] == casing["match"] == "ad"
    assert casing["product_code"] == "BAGIRSAK" and D(casing["unit_price"]) == D("11.60")
    assert any("Lot numarası yok" in w for w in casing["warnings"])
    assert any("tutar" in w.lower() for w in casing["warnings"])  # 6 × 11,60 = 69,60 ≠ 70,00
    # Hiçbir şey kaydedilmedi.
    assert session.scalars(select(Lot).where(Lot.lot_no == "ET-2026-002")).first() is None
    store = auth_header(client, "magaza1", "magaza123")
    assert (
        client.post(f"{API}/purchases/parse-text", json={"text": INVOICE}, headers=store).status_code == 403
    )


def test_parse_invoice_text_reports_missing_parts(session):
    result = parse_invoice_text(session, "merhaba dünya")
    assert result.lines == [] and result.supplier_id is None and len(result.warnings) == 4


@pytest.mark.parametrize(
    ("text", "value"),
    [
        ("1.188,00", "1188.00"),
        ("9,90", "9.90"),
        ("9.90", "9.90"),
        ("1.188", "1188"),
        ("1,188.50", "1188.50"),
        ("120", "120"),
    ],
)
def test_parse_number_handles_turkish_and_english(text, value):
    assert parse_number(text) == D(value)


# --- Hesaplayıcılar ---


def test_ekp_calculator_matches_scenario(client, admin):
    body = {
        "raw_lines": [
            {"name": "Et", "qty": "100", "unit_price": "9.70"},
            {"name": "Baharat", "qty": "2", "unit_price": "24.00"},
            {"name": "Bağırsak", "qty": "5", "unit_price": "11.60"},
        ],
        "service_unit_price": "5.50",
        "received_qty": "85",
        "invoiced_qty": "86",
        "sale_price": "24.90",
    }
    result = client.post(f"{API}/calc/ekp", json=body, headers=admin).json()
    assert D(result["raw_total"]) == D("1076.00") and D(result["service_used"]) == D("467.50")
    assert D(result["ekp_display"]) == D("18.16")
    assert any("86" in w for w in result["warnings"])  # fatura 86 adet, teslim 85


def test_cutting_calculator_allocates_whole_cost_and_checks_balance(client, admin):
    lines = [
        {"name": "But", "kg": "7", "value_per_kg": "14"},
        {"name": "Sırt", "kg": "4", "value_per_kg": "18"},
        {"name": "Fire", "kg": "3", "is_fire": True},
    ]
    body = {
        "input_kg": "15",
        "input_cost": "351.00",
        "method": "DEGER",
        "tolerance_kg": "0.5",
        "lines": lines,
    }
    result = client.post(f"{API}/calc/cutting", json=body, headers=admin).json()
    assert D(result["total_allocated"]) == D("351.00")
    assert result["lines"][2]["allocated_cost"] == "0.00" and result["lines"][2]["unit_cost"] is None
    assert result["balance_ok"] is False and D(result["difference_kg"]) == D(1)
    assert any("Ağırlık dengesi" in w for w in result["warnings"])


# --- Panel grafikleri ---


def test_dashboard_charts_show_scenario_costs_and_shipments(client, admin, session):
    build_demo_scenario(session)
    body = client.get(f"{API}/dashboard/charts", headers=admin).json()
    assert body["cost_order_no"] == "URT-2026-045" and D(body["cost_ekp"]) == D("18.16")
    assert sum(D(s["value"]) for s in body["cost_slices"]) == D("1543.50")
    assert {s["customer"]: D(s["qty_by_unit"]["adet"]) for s in body["shipments"]} == {
        "Market A": D(30),
        "Market B": D(25),
        "Market C": D(30),
    }
    assert body["ekp_history"][-1]["label"] == "URT-2026-045" and body["ekp_history"][-1]["forecast"]
    assert D(body["fill_rate_pct"]) == D(100)
    assert body["parts_cutting_no"] and len(body["part_costs"]) == 5
    assert len(body["ekp_synthetic"]) >= 5  # model test verisi (sentetik)


def test_alarm_visible_kinds_helper():
    class _U:
        role = None

    from app.models.enums import UserRole  # noqa: PLC0415

    user = _U()
    user.role = UserRole.DEPO
    assert AlertKind.HATALI_GIRIS not in alarms.visible_kinds(user)  # type: ignore[arg-type]
    user.role = UserRole.YONETICI
    assert AlertKind.HATALI_GIRIS in alarms.visible_kinds(user)  # type: ignore[arg-type]
