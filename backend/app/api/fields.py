"""API yanıtlarında ortak alan tipleri."""

from datetime import UTC, datetime
from typing import Annotated

from pydantic import AfterValidator


def _as_utc(value: datetime) -> datetime:
    return value if value.tzinfo else value.replace(tzinfo=UTC)


# Veritabanı zamanları saat dilimsiz UTC tutar; API bunları saat dilimi ekiyle verir (api.md §1, ISO 8601).
UtcDateTime = Annotated[datetime, AfterValidator(_as_utc)]
