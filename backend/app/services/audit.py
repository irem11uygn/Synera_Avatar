"""Denetim günlüğü: kim, ne zaman, ne yaptı (NFR-008).

Kayıt isteğin kendi işleminde yazılır: işlem geri alınırsa (hata) günlük kaydı da yazılmamış olur;
yani günlükte yalnız gerçekten olmuş işler görünür. Hatalı girişler bu kuralın istisnasıdır: API
o isteği hata fırlatmadan yanıtlar, kayıt kalıcı olur (bkz. api/auth.py).
"""

from dataclasses import dataclass
from datetime import date

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.domain.clock import business_day_bounds_utc
from app.models import AuditEvent, User
from app.models.enums import Severity


def log(
    session: Session,
    action: str,
    message: str,
    *,
    user: User | None = None,
    username: str | None = None,
    severity: Severity = Severity.BILGI,
    ref_type: str | None = None,
    ref_id: int | None = None,
    client: str | None = None,
) -> AuditEvent:
    event = AuditEvent(
        user_id=user.id if user else None,
        username=(user.username if user else username or None),
        severity=severity,
        action=action,
        message=message[:500],
        ref_type=ref_type,
        ref_id=ref_id,
        client=client[:64] if client else None,
    )
    session.add(event)
    session.flush()
    return event


@dataclass(frozen=True)
class AuditFilter:
    text: str | None = None
    severity: Severity | None = None
    username: str | None = None
    day_from: date | None = None  # iş günü (yerel saat)
    day_to: date | None = None
    limit: int = 500


def search(session: Session, f: AuditFilter) -> list[AuditEvent]:
    query = select(AuditEvent).order_by(AuditEvent.id.desc()).limit(min(max(f.limit, 1), 5000))
    if f.text:
        pattern = f"%{f.text.strip()}%"
        query = query.where(
            or_(
                AuditEvent.message.ilike(pattern),
                AuditEvent.action.ilike(pattern),
                AuditEvent.username.ilike(pattern),
            )
        )
    if f.severity:
        query = query.where(AuditEvent.severity == f.severity)
    if f.username:
        query = query.where(AuditEvent.username == f.username)
    if f.day_from:
        query = query.where(AuditEvent.created_at >= business_day_bounds_utc(f.day_from)[0])
    if f.day_to:
        query = query.where(AuditEvent.created_at < business_day_bounds_utc(f.day_to)[1])
    return list(session.scalars(query))
