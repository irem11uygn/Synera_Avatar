"""Testlerde ortak kullanılan küçük yardımcılar."""

from pathlib import Path

from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Lot

BACKEND_DIR = Path(__file__).resolve().parents[1]


def alembic_config() -> Config:
    config = Config(str(BACKEND_DIR / "alembic.ini"))
    config.set_main_option("script_location", str(BACKEND_DIR / "migrations"))
    return config


def by_code[T](session: Session, model: type[T], code: str) -> T:
    """Ana veri kaydını koduyla getirir (ör. Product 'ET', Warehouse 'ANA')."""
    return session.scalars(select(model).where(model.code == code)).one()  # type: ignore[attr-defined]


def lot_by_no(session: Session, lot_no: str) -> Lot:
    return session.scalars(select(Lot).where(Lot.lot_no == lot_no)).one()


def auth_header(client: TestClient, username: str, password: str) -> dict[str, str]:
    """Demo kullanıcısıyla giriş yapar ve Authorization başlığını döndürür."""
    response = client.post("/api/v1/auth/login", json={"username": username, "password": password})
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['token']}"}
