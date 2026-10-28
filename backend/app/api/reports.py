"""Raporlar (FR-601…FR-607): JSON ya da ?format=csv."""

from datetime import UTC, date, datetime
from decimal import Decimal
from enum import Enum
from typing import Literal

from fastapi import APIRouter, Response
from pydantic import BaseModel, Field

from app.api.csv_export import csv_response, csv_text
from app.api.deps import Db, WebUser
from app.models.enums import MailStatus
from app.services import audit, mail, report_mail
from app.services.reports import FILTERS, META, ColumnKind, Report, ReportCode, ReportFilter, build_report

router = APIRouter(prefix="/reports", tags=["raporlar"])

Value = str | int | bool | None


class ColumnOut(BaseModel):
    key: str
    label: str
    kind: ColumnKind


class ReportOut(BaseModel):
    code: ReportCode
    title: str
    description: str
    filters: list[str]
    columns: list[ColumnOut]
    rows: list[dict[str, Value]]
    totals: dict[str, Value]
    notes: list[str]


class ReportInfoOut(BaseModel):
    code: ReportCode
    title: str
    description: str
    filters: list[str]


def _json_value(value: object) -> Value:
    """Ondalıklar metin (ADR-006), zamanlar ISO 8601 (sunucu zamanı UTC, 'Z' ekiyle)."""
    if value is None or isinstance(value, bool | int | str):
        return value  # type: ignore[return-value]
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, datetime):
        return value.replace(tzinfo=UTC).isoformat().replace("+00:00", "Z")
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, Enum):
        return str(value.value)
    return str(value)


def _report_out(report: Report) -> ReportOut:
    return ReportOut(
        code=report.code,
        title=report.title,
        description=report.description,
        filters=list(FILTERS[report.code]),
        columns=[ColumnOut(key=c.key, label=c.label, kind=c.kind) for c in report.columns],
        rows=[{c.key: _json_value(row.get(c.key)) for c in report.columns} for row in report.rows],
        totals={key: _json_value(value) for key, value in report.totals.items()},
        notes=report.notes,
    )


@router.get("", response_model=list[ReportInfoOut])
def list_reports(_: WebUser) -> list[ReportInfoOut]:
    return [
        ReportInfoOut(code=code, title=META[code][0], description=META[code][1], filters=list(FILTERS[code]))
        for code in ReportCode
    ]


@router.get("/{code}", response_model=ReportOut, responses={200: {"content": {"text/csv": {}}}})
def get_report(
    code: ReportCode,
    db: Db,
    _: WebUser,
    date_from: date | None = None,
    date_to: date | None = None,
    product_id: int | None = None,
    lot_no: str | None = None,
    format: Literal["json", "csv"] = "json",
) -> ReportOut | Response:
    report = build_report(
        db,
        code,
        ReportFilter(
            date_from=date_from, date_to=date_to, product_id=product_id, lot_no=(lot_no or "").strip() or None
        ),
    )
    if format == "csv":
        return csv_response(
            f"rapor_{code.value}.csv",
            [c.label for c in report.columns],
            ([row.get(c.key) for c in report.columns] for row in report.rows),
        )
    return _report_out(report)


class ReportEmailIn(BaseModel):
    recipients: list[str] = Field(min_length=1, max_length=20)
    note: str | None = Field(default=None, max_length=1000)


class ReportEmailOut(BaseModel):
    message_id: int
    status: MailStatus
    recipients: list[str]
    subject: str
    attachment: str


@router.post("/{code}/email", response_model=ReportEmailOut, status_code=202, responses={422: {}, 429: {}})
def email_report(
    code: ReportCode,
    body: ReportEmailIn,
    db: Db,
    user: WebUser,
    date_from: date | None = None,
    date_to: date | None = None,
    product_id: int | None = None,
    lot_no: str | None = None,
) -> ReportEmailOut:
    """Raporu CSV ekiyle e-postayla gönderir (202: giden kutusuna alındı, istek SMTP'yi beklemez).

    Süzgeçler `GET /reports/{code}` ile aynıdır. Alıcı: aktif kullanıcı ya da izinli alan adı.
    Kullanıcı başına dakikada en çok 5 gönderim.
    """
    report_mail.limiter.check(user.id)
    recipients = report_mail.allowed_recipients(db, body.recipients)
    filters = ReportFilter(
        date_from=date_from, date_to=date_to, product_id=product_id, lot_no=(lot_no or "").strip() or None
    )
    report = build_report(db, code, filters)
    attachment = report_mail.csv_attachment(
        report,
        csv_text(
            [c.label for c in report.columns],
            ([row.get(c.key) for c in report.columns] for row in report.rows),
        ),
    )
    subject, html_body, text = report_mail.report_mail(report, filters, user, body.note, attachment)
    message = mail.queue(
        db,
        recipients=recipients,
        subject=subject,
        body=text,
        html=html_body,
        attachment=attachment,
        kind="RAPOR",
        user=user,
    )
    assert message is not None  # tekilleştirme anahtarı yok
    audit.log(
        db,
        "RAPOR_EPOSTA",
        f"{report.title} ({code.value}) e-postayla gönderildi → {', '.join(recipients)}",
        user=user,
        ref_type="MAIL",
        ref_id=message.id,
    )
    report_mail.limiter.record(user.id)
    return ReportEmailOut(
        message_id=message.id,
        status=message.status,
        recipients=recipients,
        subject=message.subject,
        attachment=attachment.filename,
    )
