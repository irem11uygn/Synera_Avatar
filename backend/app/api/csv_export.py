"""CSV dışa aktarma: Türkçe Excel'in doğrudan açabileceği biçim (api.md §1 "CSV").

Ayırıcı noktalı virgül, ondalık ayırıcı virgül, UTF-8 BOM (Excel Türkçe karakterleri doğru okusun).
Binlik ayırıcı yazılmaz; hücreler sayı olarak okunur.
"""

import csv
import io
from collections.abc import Iterable, Sequence
from datetime import date, datetime
from decimal import Decimal
from enum import Enum

from fastapi import Response


def cell(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, Decimal):
        return format(value.normalize(), "f").replace(".", ",")
    if isinstance(value, bool):
        return "Evet" if value else "Hayır"
    if isinstance(value, datetime):
        return value.strftime("%Y-%m-%d %H:%M")
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, Enum):
        return str(value.value)
    return _safe_text(str(value))


def _safe_text(text: str) -> str:
    """Excel'de formül olarak çalışabilecek metinler (=, +, -, @, sekme ile başlayan) düz metne çevrilir
    (OWASP "CSV injection"). Sayısal hücreler bu yola girmez."""
    return "'" + text if text[:1] in ("=", "+", "-", "@", "\t", "\r") else text


def csv_response(filename: str, header: Sequence[str], rows: Iterable[Sequence[object]]) -> Response:
    buffer = io.StringIO()
    writer = csv.writer(buffer, delimiter=";", lineterminator="\r\n")
    writer.writerow(header)
    for row in rows:
        writer.writerow([cell(value) for value in row])
    return Response(
        content="﻿" + buffer.getvalue(),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
