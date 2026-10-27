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
    )
