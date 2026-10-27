"""Raporlar (FR-601…FR-607): JSON ya da ?format=csv."""

from datetime import UTC, date, datetime
from decimal import Decimal
from enum import Enum
from typing import Literal

from fastapi import APIRouter, Response
from pydantic import BaseModel

from app.api.csv_export import csv_response
from app.api.deps import Db, WebUser
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
