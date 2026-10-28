"""Rapor ve alarm e-postaları: alıcı listesi, kuyruğa koyma, giden kutusu, elle gönderme."""

from typing import Literal

from fastapi import APIRouter
from pydantic import BaseModel, Field
from sqlalchemy import select

from app.api.deps import AdminUser, Db, WebUser
from app.api.fields import UtcDateTime
from app.config import get_settings
from app.errors import InvalidState
from app.models import MailMessage, Partner, User
from app.models.enums import MailStatus, UserRole
from app.services import audit, mail
from app.services.lookups import get_or_404

router = APIRouter(prefix="/mail", tags=["e-posta"])


class MailStatusOut(BaseModel):
    smtp_configured: bool
    host: str | None
    sender: str | None


class RecipientOut(BaseModel):
    name: str
    email: str
    group: Literal["Kullanıcı", "Müşteri", "Tedarikçi", "Dış üretici"]
    role: UserRole | None


class MailIn(BaseModel):
    recipients: list[str] = Field(min_length=1, max_length=mail.MAX_RECIPIENTS)
    subject: str = Field(min_length=1, max_length=200)
    body: str = Field(min_length=1, max_length=mail.MAX_BODY)


class MailOut(BaseModel):
    id: int
    created_at: UtcDateTime
    created_by_name: str | None
    kind: str
    recipients: str
    subject: str
    body: str
    status: MailStatus
    attempts: int
    sent_at: UtcDateTime | None
    last_error: str | None


class DeliveryOut(BaseModel):
    sent: int
    failed: int


def _out(db: Db, message: MailMessage) -> MailOut:
    by = db.get(User, message.created_by) if message.created_by else None
    return MailOut(
        id=message.id,
        created_at=message.created_at,
        created_by_name=by.full_name if by else "Sistem (alarm)",
        kind=message.kind,
        recipients=message.recipients,
        subject=message.subject,
        body=message.body,
        status=message.status,
        attempts=message.attempts,
        sent_at=message.sent_at,
        last_error=message.last_error,
    )


@router.get("/status", response_model=MailStatusOut)
def status(_: WebUser) -> MailStatusOut:
    smtp = get_settings().smtp
    return MailStatusOut(
        smtp_configured=smtp is not None,
        host=smtp.host if smtp else None,
        sender=smtp.sender if smtp else None,
    )


@router.get("/recipients", response_model=list[RecipientOut])
def recipients(db: Db, _: WebUser) -> list[RecipientOut]:
    """E-postası tanımlı aktif kullanıcılar ve cari kartlar (müşteri, tedarikçi, dış üretici)."""
    rows = [
        RecipientOut(name=u.full_name, email=u.email, group="Kullanıcı", role=u.role)
        for u in db.scalars(select(User).where(User.active, User.email.is_not(None)).order_by(User.full_name))
        if u.email
    ]
    for p in db.scalars(select(Partner).where(Partner.email.is_not(None)).order_by(Partner.name)):
        if not p.email:
            continue
        group = "Müşteri" if p.is_customer else "Dış üretici" if p.is_subcontractor else "Tedarikçi"
        rows.append(RecipientOut(name=p.name, email=p.email, group=group, role=None))
    return rows


@router.post("", response_model=MailOut, status_code=201)
def send(body: MailIn, db: Db, user: WebUser) -> MailOut:
    """Raporu giden kutusuna koyar; e-posta sunucusu tanımlıysa arka planda gönderilir."""
    message = mail.queue(
        db, recipients=body.recipients, subject=body.subject, body=body.body, kind="RAPOR", user=user
    )
    audit.log(
        db,
        "EPOSTA",
        f'E-posta kuyruğa alındı: "{message.subject}" → {message.recipients}',
        user=user,
        ref_type="MAIL",
        ref_id=message.id,
    )
    return _out(db, message)


@router.get("/outbox", response_model=list[MailOut])
def outbox(db: Db, user: WebUser, limit: int = 200) -> list[MailOut]:
    """Yönetici bütün e-postaları, diğer kullanıcılar yalnız kendi gönderdiklerini görür."""
    query = select(MailMessage).order_by(MailMessage.id.desc()).limit(min(max(limit, 1), 1000))
    if user.role != UserRole.YONETICI:
        query = query.where(MailMessage.created_by == user.id)
    return [_out(db, m) for m in db.scalars(query)]


@router.post("/deliver", response_model=DeliveryOut)
def deliver(db: Db, user: AdminUser) -> DeliveryOut:
    """Kuyruktaki ve hatalı e-postaları şimdi gönderir (arka plan göndericisini beklemeden)."""
    smtp = get_settings().smtp
    if smtp is None:
        raise InvalidState(
            "E-posta sunucusu (SMTP) tanımlı değil; e-postalar kuyrukta bekliyor. Kurulum: .env dosyasında "
            "SMTP_HOST ve diğer SMTP_ ayarları."
        )
    result = mail.deliver_pending(db, smtp, include_exhausted=True, limit=100)
    audit.log(
        db,
        "EPOSTA",
        f"Giden kutusu elle gönderildi: {result.sent} gönderildi, {result.failed} hatalı.",
        user=user,
    )
    return DeliveryOut(sent=result.sent, failed=result.failed)


@router.post("/{message_id}/retry", response_model=MailOut)
def retry(message_id: int, db: Db, user: AdminUser) -> MailOut:
    message = get_or_404(db, MailMessage, message_id, "E-posta")
    if message.status == MailStatus.GONDERILDI:
        raise InvalidState("Bu e-posta zaten gönderildi.")
    message.status, message.attempts, message.last_error = MailStatus.KUYRUKTA, 0, None
    db.flush()
    audit.log(db, "EPOSTA", f'E-posta yeniden kuyruğa alındı: "{message.subject}"', user=user)
    return _out(db, message)
