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
    smtp: "SmtpSettings | None"  # None: e-posta kapalı (SMTP_HOST boş), e-postalar giden kutusunda bekler
    allowed_email_domains: tuple[str, ...]  # rapor e-postasında kullanıcılar dışında izinli alan adları
    web_base_url: str  # e-postalardaki bağlantılar için web arayüzünün adresi


@dataclass(frozen=True)
class SmtpSettings:
    host: str
    port: int
    username: str | None  # doluysa STARTTLS + giriş yapılır
    password: str | None
    sender: str
    interval_s: int  # arka plan göndericisi en geç kaç saniyede bir kuyruğa bakar


def _smtp_settings() -> SmtpSettings | None:
    # Varsayılan docker-compose'daki Mailpit (yerel test kutusu); SMTP_HOST= (boş) e-postayı kapatır.
    host = os.environ.get("SMTP_HOST", "mailpit").strip()
    if not host:
        return None
    return SmtpSettings(
        host=host,
        port=int(os.environ.get("SMTP_PORT", "1025")),
        username=os.environ.get("SMTP_USER") or None,
        # SMTP_PASSWORD ve SMTP_FROM: aynı gün önce kullanılan adlar, geriye uyum için okunur.
        password=os.environ.get("SMTP_PASS") or os.environ.get("SMTP_PASSWORD") or None,
        sender=os.environ.get("MAIL_FROM")
        or os.environ.get("SMTP_FROM")
        or "AVATAR Synera <avatar@localhost>",
        interval_s=int(os.environ.get("MAIL_INTERVAL_S", "30")),
    )


def _domains(raw: str) -> tuple[str, ...]:
    return tuple(d.strip().lower().lstrip("@") for d in raw.split(",") if d.strip())


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
        allowed_email_domains=_domains(os.environ.get("ALLOWED_EMAIL_DOMAINS", "")),
        web_base_url=os.environ.get("WEB_BASE_URL", "http://localhost:8080").rstrip("/"),
    )
