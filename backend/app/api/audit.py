"""Denetim günlüğü (yalnız yönetici): arama, süzme, CSV."""

from datetime import date

from fastapi import APIRouter, Response
from pydantic import BaseModel
from sqlalchemy import select

from app.api.csv_export import csv_response
from app.api.deps import AdminUser, Db
from app.api.fields import UtcDateTime
from app.domain.clock import business_zone
from app.models import AuditEvent, User
from app.models.enums import Severity
from app.services import audit
from app.services.audit import AuditFilter

router = APIRouter(prefix="/audit", tags=["denetim"])


class AuditOut(BaseModel):
    id: int
    created_at: UtcDateTime
    username: str | None
    full_name: str | None
    severity: Severity
    action: str
    message: str
    ref_type: str | None
    ref_id: int | None
    client: str | None


def _rows(db: Db, events: list[AuditEvent]) -> list[AuditOut]:
    names = {user_id: name for user_id, name in db.execute(select(User.id, User.full_name))}
    return [
        AuditOut(
            id=e.id,
            created_at=e.created_at,
            username=e.username,
            full_name=names.get(e.user_id) if e.user_id else None,
            severity=e.severity,
            action=e.action,
            message=e.message,
            ref_type=e.ref_type,
            ref_id=e.ref_id,
            client=e.client,
        )
        for e in events
    ]


@router.get("", response_model=list[AuditOut])
def list_events(
    db: Db,
    _: AdminUser,
    q: str | None = None,
    severity: Severity | None = None,
    username: str | None = None,
    day_from: date | None = None,
    day_to: date | None = None,
    limit: int = 500,
) -> list[AuditOut]:
    f = AuditFilter(
        text=q, severity=severity, username=username, day_from=day_from, day_to=day_to, limit=limit
    )
    return _rows(db, audit.search(db, f))


@router.get("/export.csv", response_class=Response)
def export_csv(
    db: Db,
    _: AdminUser,
    q: str | None = None,
    severity: Severity | None = None,
    username: str | None = None,
    day_from: date | None = None,
    day_to: date | None = None,
) -> Response:
    f = AuditFilter(
        text=q, severity=severity, username=username, day_from=day_from, day_to=day_to, limit=5000
    )
    zone = business_zone()
    rows = [
        [
            r.created_at.astimezone(zone).replace(tzinfo=None),
            r.username,
            r.full_name,
            r.severity,
            r.action,
            r.message,
            r.client,
        ]
        for r in _rows(db, audit.search(db, f))
    ]
    header = ["Zaman (yerel)", "Kullanıcı", "Ad soyad", "Önem", "İşlem", "Açıklama", "Adres"]
    return csv_response("denetim_gunlugu.csv", header, rows)
