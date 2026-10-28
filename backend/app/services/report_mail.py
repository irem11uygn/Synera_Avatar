"""Raporu e-postayla gönderme: ek ve metin. Alıcı kuralı ve gönderim sınırı services/mail_policy.py'de
(rapor alıcısı yalnız aktif kullanıcı ya da izinli alan adı). Ek, rapor ekranının "CSV indir" düğmesiyle
aynı dosyadır (sistemde PDF üretimi yok).
"""

import html

from app import mailer
from app.config import get_settings
from app.mailer import Attachment
from app.models import User
from app.services.reports import Report, ReportFilter


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
