"""Ortam değişkenlerinden okunan ayarlar (örnekler: kök dizindeki .env.example)."""

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

# Yerel çalıştırmada depo kökündeki data/seed; Docker imajında SEED_DIR ile verilir.
_DEFAULT_SEED_DIR = Path(__file__).resolve().parents[2] / "data" / "seed"


@dataclass(frozen=True)
class Settings:
    database_url: str
    log_level: str
    seed_profile: str
    seed_dir: Path
    business_utc_offset_hours: int  # iş günü (üretim tarihi, SKT, gün sonu) yerel saate göre
    smtp: "SmtpSettings | None"  # tanımlı değilse e-postalar giden kutusunda "kuyrukta" bekler


@dataclass(frozen=True)
class SmtpSettings:
    host: str
    port: int
    username: str | None
    password: str | None
    sender: str
    starttls: bool
    interval_s: int  # giden kutusu kaç saniyede bir taranır


def _smtp_settings() -> SmtpSettings | None:
    host = os.environ.get("SMTP_HOST", "").strip()
    if not host:
        return None
    return SmtpSettings(
        host=host,
        port=int(os.environ.get("SMTP_PORT", "587")),
        username=os.environ.get("SMTP_USER") or None,
        password=os.environ.get("SMTP_PASSWORD") or None,
        sender=os.environ.get("SMTP_FROM") or os.environ.get("SMTP_USER") or "synera@localhost",
        starttls=os.environ.get("SMTP_STARTTLS", "true").lower() not in ("0", "false", "hayir"),
        interval_s=int(os.environ.get("MAIL_INTERVAL_S", "30")),
    )


@lru_cache
def get_settings() -> Settings:
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        raise RuntimeError("DATABASE_URL ortam değişkeni tanımlı değil (bkz. .env.example).")
    return Settings(
        database_url=database_url,
        log_level=os.environ.get("LOG_LEVEL", "INFO"),
        seed_profile=os.environ.get("SEED_PROFILE", "demo"),
        seed_dir=Path(os.environ.get("SEED_DIR", _DEFAULT_SEED_DIR)),
        business_utc_offset_hours=int(os.environ.get("BUSINESS_UTC_OFFSET_HOURS", "3")),  # Türkiye UTC+3
        smtp=_smtp_settings(),
    )
