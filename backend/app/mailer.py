"""E-posta gönderimi: yalnız standart kütüphane (smtplib, email); ek bağımlılık yok.

Ayarlar ortam değişkenlerinden (app/config.py): SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASS, MAIL_FROM.
Varsayılan docker-compose'daki Mailpit'tir (kimlik doğrulamasız, 1025). SMTP_USER doluysa STARTTLS ve
giriş yapılır; 465 portunda doğrudan TLS.

`send_mail` hiçbir zaman hata fırlatmaz: SMTP ya da bağlantı hatası günlüğe yazılır ve sonuç
(başarılı/başarısız, alıcılar, zaman, hata) döner. Sonucu kalıcı yazan giden kutusudur (services/mail.py);
API istekleri e-postayı beklemez.
"""

import html
import logging
import smtplib
import ssl
from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass
from datetime import datetime
from email.message import EmailMessage
from email.utils import formatdate, make_msgid, parseaddr
from html.parser import HTMLParser

from app.config import SmtpSettings, get_settings
from app.models.types import utcnow

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class Attachment:
    filename: str
    content: bytes
    mime: str  # ör. "text/csv", "application/pdf"


@dataclass(frozen=True)
class MailResult:
    ok: bool
    recipients: list[str]
    at: datetime  # UTC, saat dilimsiz (veritabanıyla aynı)
    error: str | None = None


Transport = Callable[[SmtpSettings], smtplib.SMTP]


def connect(settings: SmtpSettings) -> smtplib.SMTP:
    """SMTP bağlantısı. Kullanıcı adı varsa STARTTLS + giriş; yoksa (Mailpit) düz bağlantı."""
    if settings.port == 465:
        client: smtplib.SMTP = smtplib.SMTP_SSL(
            settings.host, settings.port, timeout=20, context=ssl.create_default_context()
        )
    else:
        client = smtplib.SMTP(settings.host, settings.port, timeout=20)
        if settings.username:
            client.starttls(context=ssl.create_default_context())
    if settings.username:
        client.login(settings.username, settings.password or "")
    return client


def build_message(
    sender: str,
    to: Sequence[str],
    subject: str,
    html_body: str,
    *,
    text: str | None = None,
    attachment: Attachment | None = None,
) -> EmailMessage:
    """HTML gövde + düz metin karşılığı (HTML göstermeyen programlar için) + isteğe bağlı tek ek."""
    message = EmailMessage()
    message["From"] = sender
    message["To"] = ", ".join(to)
    message["Subject"] = subject
    message["Date"] = formatdate(localtime=False)
    domain = parseaddr(sender)[1].rpartition("@")[2] or "localhost"
    message["Message-ID"] = make_msgid(domain=domain)
    message.set_content(text if text is not None else html_to_text(html_body))
    message.add_alternative(html_body, subtype="html")
    if attachment is not None:
        maintype, _, subtype = attachment.mime.partition("/")
        message.add_attachment(
            attachment.content,
            maintype=maintype or "application",
            subtype=subtype or "octet-stream",
            filename=attachment.filename,
        )
    return message


def send_mail(
    to: Sequence[str] | str,
    subject: str,
    html_body: str,
    attachment: Attachment | None = None,
    *,
    text: str | None = None,
    settings: SmtpSettings | None = None,
    transport: Transport = connect,
) -> MailResult:
    recipients = [to] if isinstance(to, str) else list(to)
    smtp = settings or get_settings().smtp
    if smtp is None:
        logger.info("E-posta kapalı (SMTP_HOST boş); gönderilmedi: %s", subject)
        return MailResult(False, recipients, utcnow(), "E-posta sunucusu tanımlı değil (SMTP_HOST boş).")
    message = build_message(smtp.sender, recipients, subject, html_body, text=text, attachment=attachment)
    try:
        client = transport(smtp)
        try:
            client.send_message(message)
        finally:
            try:
                client.quit()
            except (smtplib.SMTPException, OSError):
                pass  # bağlantı zaten kopmuş olabilir; gönderim sonucu değişmez
    except (smtplib.SMTPException, OSError) as error:
        logger.warning("E-posta gönderilemedi (%s → %s): %s", subject, ", ".join(recipients), error)
        return MailResult(False, recipients, utcnow(), f"{type(error).__name__}: {error}"[:500])
    logger.info("E-posta gönderildi: %s → %s", subject, ", ".join(recipients))
    return MailResult(True, recipients, utcnow())


class _TextExtractor(HTMLParser):
    BLOCK = {"p", "div", "br", "tr", "h1", "h2", "h3", "table", "ul", "ol"}

    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []
        self._href: str | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in self.BLOCK:
            self.parts.append("\n")
        elif tag == "li":
            self.parts.append("\n• ")
        elif tag == "td":
            self.parts.append("  ")
        elif tag == "a":
            href = dict(attrs).get("href")
            if href:
                self._href = href

    def handle_endtag(self, tag: str) -> None:
        if tag == "a" and self._href:
            self.parts.append(f" ({self._href})")
            self._href = None
        if tag in {"p", "h1", "h2", "h3", "table"}:
            self.parts.append("\n")

    def handle_data(self, data: str) -> None:
        self.parts.append(data)


def html_to_text(html_body: str) -> str:
    parser = _TextExtractor()
    parser.feed(html_body)
    text = "\n".join(" ".join(line.split()) for line in "".join(parser.parts).splitlines())
    while "\n\n\n" in text:
        text = text.replace("\n\n\n", "\n\n")
    return text.strip()


def html_rows(rows: Iterable[tuple[str, str]]) -> str:
    """E-posta gövdesindeki iki sütunlu bilgi tablosunun satırları (değerler kaçışlı)."""
    label = "padding:4px 14px 4px 0;color:#5f7372"
    return "".join(
        f'<tr><td style="{label}">{html.escape(k)}</td><td style="padding:4px 0">{html.escape(v)}</td></tr>'
        for k, v in rows
    )


def text_to_html(text: str) -> str:
    """Düz metin gövdeyi (eski giden kutusu kayıtları) güvenli HTML'e çevirir."""
    paragraphs = [p for p in text.split("\n\n") if p.strip()]
    return "".join(f"<p>{html.escape(p).replace(chr(10), '<br>')}</p>" for p in paragraphs)
