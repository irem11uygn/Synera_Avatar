"""Raporu e-postayla gönderme: alıcı denetimi (açık posta rölesi yok), gönderim sınırı, ek ve metin.

- Alıcı yalnız sistemdeki aktif bir kullanıcının e-postası ya da ALLOWED_EMAIL_DOMAINS'teki bir alan
  adı olabilir; başka adres 422.
- Kullanıcı başına dakikada en çok 5 gönderim (süreç belleğinde; tek sunucu süreci için yeterli).
- Ek, rapor ekranının "CSV indir" düğmesiyle aynı dosyadır (sistemde PDF üretimi yok).
"""

import html
import threading
import time
from collections import defaultdict, deque
from collections.abc import Iterable

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app import mailer
from app.config import get_settings
from app.errors import InvalidInput, TooManyAttempts
from app.mailer import Attachment
from app.models import User
from app.services.mail import clean_recipients
from app.services.reports import Report, ReportFilter

MAX_PER_WINDOW = 5
WINDOW_S = 60


class SendLimiter:
    """Anahtar (kullanıcı) başına son WINDOW_S saniyedeki gönderimler."""

    def __init__(self, max_events: int = MAX_PER_WINDOW, window_s: float = WINDOW_S) -> None:
        self.max_events = max_events
        self.window_s = window_s
        self._events: dict[int, deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    def check(self, user_id: int) -> None:
        now = time.monotonic()
        with self._lock:
            events = self._events[user_id]
            while events and now - events[0] > self.window_s:
                events.popleft()
            if len(events) >= self.max_events:
                wait = int(self.window_s - (now - events[0])) + 1
                raise TooManyAttempts(
                    f"Dakikada en çok {self.max_events} rapor e-postası gönderebilirsiniz; "
                    f"{wait} saniye sonra yeniden deneyin.",
                    retry_after_s=wait,
                )

    def record(self, user_id: int) -> None:
        with self._lock:
            self._events[user_id].append(time.monotonic())

    def reset(self) -> None:
        with self._lock:
            self._events.clear()


limiter = SendLimiter()


def allowed_recipients(session: Session, addresses: Iterable[str]) -> list[str]:
    """Biçimi doğru ve izinli alıcılar; izinsiz adres varsa hepsi birden bildirilir (422)."""
    recipients = clean_recipients(addresses)
    known = {
        email.lower()
        for email in session.scalars(
            select(func.lower(User.email)).where(User.active, User.email.is_not(None))
        )
        if email
    }
    domains = get_settings().allowed_email_domains
    rejected = [
        address
        for address in recipients
        if address.lower() not in known and address.rpartition("@")[2].lower() not in domains
    ]
    if rejected:
        raise InvalidInput(
            "Bu adreslere rapor gönderilemez: " + ", ".join(rejected) + ". Alıcı sistemde kayıtlı aktif bir "
            "kullanıcı olmalı ya da adresin alan adı izinli listede (ALLOWED_EMAIL_DOMAINS) bulunmalı.",
            rejected=rejected,
        )
    return recipients


def csv_attachment(report: Report, csv_content: str) -> Attachment:
    return Attachment(f"rapor_{report.code.value}.csv", csv_content.encode("utf-8"), "text/csv")


def _filters_text(filters: ReportFilter) -> list[tuple[str, str]]:
    rows = []
    if filters.date_from or filters.date_to:
        start = f"{filters.date_from:%d.%m.%Y}" if filters.date_from else "…"
        end = f"{filters.date_to:%d.%m.%Y}" if filters.date_to else "…"
        rows.append(("Tarih", f"{start} – {end}"))
    if filters.lot_no:
        rows.append(("Lot", filters.lot_no))
    if filters.product_id:
        rows.append(("Ürün kimliği", str(filters.product_id)))
    return rows


def report_mail(
    report: Report, filters: ReportFilter, sender: User, note: str | None, attachment: Attachment
) -> tuple[str, str, str]:
    """Konu, HTML ve düz metin gövde."""
    base = get_settings().web_base_url
    link = f"{base}/raporlar/{report.code.value}"
    rows = [
        ("Gönderen", f"{sender.full_name} ({sender.username})"),
        ("Satır sayısı", str(len(report.rows))),
        *_filters_text(filters),
        ("Ek", attachment.filename),
    ]
    esc = html.escape
    note_html = (
        f'<p style="margin:0 0 14px;padding:10px 12px;background:#f0f9f7;border-radius:8px">'
        f"{esc(note.strip()).replace(chr(10), '<br>')}</p>"
        if note and note.strip()
        else ""
    )
    table = mailer.html_rows(rows)
    notes = "".join(f"<li>{esc(n)}</li>" for n in report.notes)
    html_body = (
        '<div style="font-family:Segoe UI,Arial,sans-serif;color:#102a2a;max-width:640px">'
        '<div style="background:#0d9488;color:#ffffff;padding:14px 18px;border-radius:10px 10px 0 0">'
        "<strong>AVATAR · Synera raporu</strong></div>"
        '<div style="border:1px solid #dbe7e5;border-top:0;padding:18px;border-radius:0 0 10px 10px">'
        f'<h2 style="margin:0 0 6px;font-size:18px">{esc(report.title)}</h2>'
        f'<p style="margin:0 0 14px;color:#3f5655">{esc(report.description)}</p>'
        f"{note_html}"
        f'<table style="border-collapse:collapse;font-size:14px">{table}</table>'
        + (f'<ul style="font-size:13px;color:#3f5655">{notes}</ul>' if notes else "")
        + f'<p style="margin:16px 0 0">Raporun güncel hâli: <a href="{esc(link)}">{esc(link)}</a></p>'
        "</div></div>"
    )
    text = "\n".join(
        [
            report.title,
            report.description,
            "",
            *([note.strip(), ""] if note and note.strip() else []),
            *(f"{k}: {v}" for k, v in rows),
            *(f"• {n}" for n in report.notes),
            "",
            f"Raporun güncel hâli: {link}",
        ]
    )
    return f"[AVATAR] {report.title}", html_body, text
