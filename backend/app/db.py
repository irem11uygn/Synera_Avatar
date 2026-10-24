"""Veritabanı bağlantısı ve ORM taban sınıfı."""

import logging
import time
from functools import lru_cache

from sqlalchemy import Engine, MetaData, create_engine, text
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import get_settings

logger = logging.getLogger(__name__)

# Kısıt adları öngörülebilir olsun diye (Alembic göçleri bu adlara dayanır).
NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_N_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    """Bütün SQLAlchemy tablolarının taban sınıfı (Alembic bunun metadata'sını kullanır)."""

    metadata = MetaData(naming_convention=NAMING_CONVENTION)


@lru_cache
def get_engine() -> Engine:
    return create_engine(get_settings().database_url, pool_pre_ping=True)


@lru_cache
def get_sessionmaker() -> sessionmaker[Session]:
    return sessionmaker(bind=get_engine(), expire_on_commit=False)


def ping_database() -> None:
    """Veritabanına basit bir sorgu gönderir; ulaşılamazsa SQLAlchemy hatası fırlatır."""
    with get_engine().connect() as conn:
        conn.execute(text("SELECT 1"))


def wait_for_database(timeout_s: float = 60, interval_s: float = 2) -> None:
    """Açılışta veritabanı hazır olana kadar bekler; süre dolarsa son hatayı fırlatır."""
    deadline = time.monotonic() + timeout_s
    while True:
        try:
            ping_database()
            return
        except OperationalError:
            if time.monotonic() >= deadline:
                raise
            logger.info("Veritabanı henüz hazır değil, %.0f sn sonra yeniden denenecek", interval_s)
            time.sleep(interval_s)
