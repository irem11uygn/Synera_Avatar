"""E-posta giden kutusu (outbox).

E-posta hiçbir zaman isteğin içinde gönderilmez: önce mail_outbox tablosuna isteğin kendi işlemiyle
yazılır. İşlem geri alınırsa e-posta da hiç oluşmamış olur (olmamış bir iş için e-posta gitmez).
İşlem kaydedildiği anda arka plandaki gönderici uyandırılır ve e-postayı hemen gönderir (gerçek zamanlı);
başarısız olursa belli aralıkla yeniden dener. Her gönderimin sonucu (durum, deneme, zaman, hata) aynı
satırda kalır. SMTP_HOST boşsa e-postalar "Kuyrukta" bekler.
"""

import logging
import re
import threading
from collections.abc import Callable, Iterable
from dataclasses import dataclass

from sqlalchemy import event, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app import mailer
from app.config import SmtpSettings
from app.errors import InvalidInput
from app.mailer import Attachment
from app.models import MailMessage, User
from app.models.enums import MailStatus

logger = logging.getLogger(__name__)

EMAIL = re.compile(r"^[^@\s,;<>\"]+@[^@\s,;<>\"]+\.[^@\s,;<>\"]+$")
MAX_RECIPIENTS = 20
MAX_BODY = 20000
MAX_AUTO_ATTEMPTS = 5  # arka plan göndericisi en çok bu kadar dener; sonra yöneticinin elle denemesi gerekir
FOOTER = "\n\n—\nBu e-posta Synera Gıda üretim ve izlenebilirlik sisteminden gönderildi."
HTML_FOOTER = (
    '<p style="color:#5f7372;font-size:12px;margin-top:24px">'
    "Bu e-posta Synera Gıda üretim ve izlenebilirlik sisteminden gönderildi.</p>"
)
_QUEUED = "mail_queued"


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
    html: str | None = None,
    attachment: Attachment | None = None,
    dedup_key: str | None = None,
) -> MailMessage | None:
    """Giden kutusuna yazar. `dedup_key` daha önce kullanıldıysa yazmaz ve None döner."""
    to = clean_recipients(recipients)
    subject = " ".join(subject.split())
    if not subject:
        raise InvalidInput("E-posta konusu boş olamaz.")
    if len(body) > MAX_BODY:
        raise InvalidInput(f"E-posta metni en çok {MAX_BODY} karakter olabilir.")
    if dedup_key and session.scalar(select(MailMessage.id).where(MailMessage.dedup_key == dedup_key)):
        return None
    message = MailMessage(
        created_by=user.id if user else None,
        kind=kind,
        recipients=", ".join(to),
        subject=subject[:200],
        body=body.rstrip() + FOOTER,
        html=(html + HTML_FOOTER) if html else None,
        alert_id=alert_id,
        attachment_name=attachment.filename if attachment else None,
        attachment_mime=attachment.mime if attachment else None,
        attachment=attachment.content if attachment else None,
        dedup_key=dedup_key,
    )
    try:
        with session.begin_nested():  # aynı anda iki istek aynı anahtarı yazarsa ikincisi vazgeçer
            session.add(message)
            session.flush()
    except IntegrityError:
        if dedup_key:
            return None
        raise
    session.info[_QUEUED] = True
    return message


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
    transport: mailer.Transport = mailer.connect,
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
    sent = failed = 0
    for message in session.scalars(query):
        attachment = (
            Attachment(
                message.attachment_name,
                message.attachment,
                message.attachment_mime or "application/octet-stream",
            )
            if message.attachment is not None and message.attachment_name
            else None
        )
        result = mailer.send_mail(
            message.recipients.split(", "),
            message.subject,
            message.html or mailer.text_to_html(message.body),
            attachment,
            text=message.body,
            settings=settings,
            transport=transport,
        )
        message.attempts += 1
        if result.ok:
            message.status, message.sent_at, message.last_error = MailStatus.GONDERILDI, result.at, None
            sent += 1
        else:
            message.status, message.last_error = MailStatus.HATA, result.error
            failed += 1
    session.flush()
    return DeliveryResult(sent, failed)


class MailWorker:
    """Arka plan göndericisi: uygulama açılışında başlar. Giden kutusuna yazan işlem kaydedilince hemen
    uyanır (gerçek zamanlı); ayrıca belli aralıkla hatalıları yeniden dener."""

    def __init__(self, settings: SmtpSettings, session_factory: Callable[[], Session]) -> None:
        self.settings = settings
        self.session_factory = session_factory
        self._stop = threading.Event()
        self._wake = threading.Event()
        self._thread = threading.Thread(target=self._run, name="eposta-gonderici", daemon=True)

    def start(self) -> None:
        global _active
        _active = self
        self._thread.start()
        logger.info("E-posta göndericisi başladı (%s:%s).", self.settings.host, self.settings.port)

    def stop(self) -> None:
        global _active
        _active = None
        self._stop.set()
        self._wake.set()
        self._thread.join(timeout=5)

    def wake(self) -> None:
        self._wake.set()

    def _run(self) -> None:
        while not self._stop.is_set():
            self._wake.wait(self.settings.interval_s)
            self._wake.clear()
            if self._stop.is_set():
                break
            try:
                with self.session_factory() as session, session.begin():
                    result = deliver_pending(session, self.settings)
                if result.sent or result.failed:
                    logger.info("E-posta: %s gönderildi, %s hatalı.", result.sent, result.failed)
            except Exception:
                logger.exception("E-posta göndericisinde beklenmeyen hata")


_active: MailWorker | None = None


@event.listens_for(Session, "after_commit")
def _wake_after_commit(session: Session) -> None:
    """Giden kutusuna yazan işlem kaydedildi: göndericiyi uyandır (kaydedilmemiş e-posta gönderilmez)."""
    if session.info.pop(_QUEUED, False) and _active is not None:
        _active.wake()


@event.listens_for(Session, "after_rollback")
def _forget_after_rollback(session: Session) -> None:
    session.info.pop(_QUEUED, None)
