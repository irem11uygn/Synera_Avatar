"""E-posta giden kutusu (outbox).

E-posta hiçbir zaman isteğin içinde gönderilmez: önce mail_outbox tablosuna isteğin kendi işlemiyle
yazılır. İşlem geri alınırsa e-posta da hiç oluşmamış olur (olmamış bir iş için e-posta gitmez).
SMTP_HOST tanımlıysa arka plandaki gönderici kuyruğu tarar ve gönderir; tanımlı değilse e-postalar
"Kuyrukta" bekler, yönetici giden kutusunda görür (e-posta programıyla elle de açabilir).
"""

import logging
import re
import smtplib
import threading
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from email.message import EmailMessage
from email.utils import formatdate, make_msgid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import SmtpSettings
from app.errors import InvalidInput
from app.models import MailMessage, User
from app.models.enums import MailStatus, Severity, UserRole
from app.models.types import utcnow

logger = logging.getLogger(__name__)

EMAIL = re.compile(r"^[^@\s,;<>\"]+@[^@\s,;<>\"]+\.[^@\s,;<>\"]+$")
MAX_RECIPIENTS = 20
MAX_BODY = 20000
MAX_AUTO_ATTEMPTS = 5  # arka plan göndericisi en çok bu kadar dener; sonra yöneticinin elle denemesi gerekir
FOOTER = "\n\n—\nBu e-posta Synera Gıda üretim ve izlenebilirlik sisteminden gönderildi."


def clean_recipients(addresses: Iterable[str]) -> list[str]:
    result: list[str] = []
    for raw in addresses:
        for part in re.split(r"[,;\s]+", raw or ""):
            address = part.strip()
            if not address:
                continue
            if not EMAIL.match(address) or len(address) > 120:
                raise InvalidInput(f"Geçersiz e-posta adresi: {address}", address=address)
            if address.lower() not in (a.lower() for a in result):
                result.append(address)
    if not result:
        raise InvalidInput("En az bir alıcı seçin ya da yazın.")
    if len(result) > MAX_RECIPIENTS:
        raise InvalidInput(f"Bir e-postada en çok {MAX_RECIPIENTS} alıcı olabilir.")
    return result


def queue(
    session: Session,
    *,
    recipients: Iterable[str],
    subject: str,
    body: str,
    kind: str,
    user: User | None = None,
    alert_id: int | None = None,
) -> MailMessage:
    to = clean_recipients(recipients)
    subject = " ".join(subject.split())
    if not subject:
        raise InvalidInput("E-posta konusu boş olamaz.")
    if len(body) > MAX_BODY:
        raise InvalidInput(f"E-posta metni en çok {MAX_BODY} karakter olabilir.")
    message = MailMessage(
        created_by=user.id if user else None,
        kind=kind,
        recipients=", ".join(to),
        subject=subject[:200],
        body=body.rstrip() + FOOTER,
        alert_id=alert_id,
    )
    session.add(message)
    session.flush()
    return message


def alarm_recipients(session: Session, severity: Severity) -> list[str]:
    """Kritik alarm: yönetici ve kalite; uyarı: yalnız yönetici. E-postası tanımlı aktif kullanıcılar."""
    roles = [UserRole.YONETICI, UserRole.KALITE] if severity == Severity.KRITIK else [UserRole.YONETICI]
    rows = session.scalars(
        select(User.email).where(User.role.in_(roles), User.active, User.email.is_not(None)).order_by(User.id)
    )
    return [email for email in rows if email]


Transport = Callable[[SmtpSettings], smtplib.SMTP]


def smtp_transport(settings: SmtpSettings) -> smtplib.SMTP:
    if settings.port == 465:
        client: smtplib.SMTP = smtplib.SMTP_SSL(settings.host, settings.port, timeout=20)
    else:
        client = smtplib.SMTP(settings.host, settings.port, timeout=20)
        if settings.starttls:
            client.starttls()
    if settings.username and settings.password:
        client.login(settings.username, settings.password)
    return client


@dataclass(frozen=True)
class DeliveryResult:
    sent: int
    failed: int


def deliver_pending(
    session: Session,
    settings: SmtpSettings,
    *,
    include_exhausted: bool = False,
    limit: int = 20,
    transport: Transport = smtp_transport,
) -> DeliveryResult:
    """Kuyruktaki (ve hatalı) e-postaları gönderir. SKIP LOCKED: iki gönderici aynı e-postayı almaz."""
    query = (
        select(MailMessage)
        .where(MailMessage.status.in_([MailStatus.KUYRUKTA, MailStatus.HATA]))
        .order_by(MailMessage.id)
        .limit(limit)
        .with_for_update(skip_locked=True)
    )
    if not include_exhausted:
        query = query.where(MailMessage.attempts < MAX_AUTO_ATTEMPTS)
    messages = list(session.scalars(query))
    if not messages:
        return DeliveryResult(0, 0)
    sent = failed = 0
    try:
        client = transport(settings)
    except Exception as error:  # sunucuya ulaşılamadı: hepsi bu turda hatalı
        for message in messages:
            _failed(message, error)
        session.flush()
        logger.warning("E-posta sunucusuna bağlanılamadı: %s", error)
        return DeliveryResult(0, len(messages))
    try:
        for message in messages:
            try:
                client.send_message(_mime(message, settings.sender))
            except Exception as error:
                _failed(message, error)
                failed += 1
                continue
            message.status, message.sent_at, message.last_error = MailStatus.GONDERILDI, utcnow(), None
            message.attempts += 1
            sent += 1
    finally:
        try:
            client.quit()
        except Exception:  # bağlantı zaten kopmuş olabilir
            pass
    session.flush()
    return DeliveryResult(sent, failed)


def _failed(message: MailMessage, error: Exception) -> None:
    message.status = MailStatus.HATA
    message.attempts += 1
    message.last_error = f"{type(error).__name__}: {error}"[:500]


def _mime(message: MailMessage, sender: str) -> EmailMessage:
    mime = EmailMessage()
    mime["From"] = sender
    mime["To"] = message.recipients
    mime["Subject"] = message.subject
    mime["Date"] = formatdate(localtime=False)
    mime["Message-ID"] = make_msgid(domain=sender.split("@")[-1] or "localhost")
    mime.set_content(message.body)
    return mime


class MailWorker:
    """Arka plan göndericisi: SMTP tanımlıysa uygulama açılışında başlar, belli aralıkla kuyruğu tarar."""

    def __init__(self, settings: SmtpSettings, session_factory: Callable[[], Session]) -> None:
        self.settings = settings
        self.session_factory = session_factory
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._run, name="eposta-gonderici", daemon=True)

    def start(self) -> None:
        self._thread.start()
        logger.info("E-posta göndericisi başladı (%s:%s).", self.settings.host, self.settings.port)

    def stop(self) -> None:
        self._stop.set()
        self._thread.join(timeout=5)

    def _run(self) -> None:
        while not self._stop.wait(self.settings.interval_s):
            try:
                with self.session_factory() as session, session.begin():
                    result = deliver_pending(session, self.settings)
                if result.sent or result.failed:
                    logger.info("E-posta: %s gönderildi, %s hatalı.", result.sent, result.failed)
            except Exception:
                logger.exception("E-posta göndericisinde beklenmeyen hata")
