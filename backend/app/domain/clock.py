"""İş günü: veritabanı zamanları UTC'dir, ama üretim tarihi, son kullanma tarihi ve gün sonu
işletmenin yerel takvimine göre hesaplanır (Türkiye UTC+3, yaz saati yok). Aksi hâlde gece
00:00–03:00 arasında yapılan işlem bir önceki güne yazılırdı.
"""

from datetime import UTC, date, datetime, time, timedelta, timezone

from app.config import get_settings


def business_zone() -> timezone:
    return timezone(timedelta(hours=get_settings().business_utc_offset_hours))


def business_today(now: datetime | None = None) -> date:
    moment = now if now is not None else datetime.now(UTC)
    if moment.tzinfo is None:  # veritabanındaki saat dilimsiz UTC
        moment = moment.replace(tzinfo=UTC)
    return moment.astimezone(business_zone()).date()


def business_day_bounds_utc(day: date) -> tuple[datetime, datetime]:
    """Yerel günün başı ve sonu, veritabanının saat dilimsiz UTC biçiminde."""
    start = datetime.combine(day, time.min, tzinfo=business_zone()).astimezone(UTC).replace(tzinfo=None)
    return start, start + timedelta(days=1)
