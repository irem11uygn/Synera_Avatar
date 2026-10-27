"""Testlerde ortak kullanılan küçük yardımcılar."""

from datetime import timedelta
from decimal import Decimal
from pathlib import Path

from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.clock import business_today
from app.models import Lot, Partner, Product, Warehouse
from app.models.enums import DocType, LotOrigin, MovementType
from app.services.ledger import create_lot

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


def make_lot(
    session, lot_no, *, product="NARIN-SUCUK", qty="40", value="300.00", days_left=5, warehouse="ANA"
):
    """Bugüne göre son kullanma tarihli, hazır alınmış bir parti (kaynak lotu gerekmez; I-8)."""
    return create_lot(
        session,
        lot_no=lot_no,
        product_id=by_code(session, Product, product).id,
        origin=LotOrigin.ALIS,
        qty=Decimal(qty),
        value=Decimal(value),
        warehouse_id=by_code(session, Warehouse, warehouse).id,
        movement_type=MovementType.ALIS_GIRIS,
        doc_type=DocType.ALIS,
        doc_id=1,
        expiry_date=business_today() + timedelta(days=days_left),
    )


def store_sale(client, headers, session, *lines, payment="KART", customer="M-A", warehouse="ANA"):
    """Mağaza (web) satışı isteği; yanıtı döndürür."""
    body = {
        "customer_id": by_code(session, Partner, customer).id,
        "warehouse_id": by_code(session, Warehouse, warehouse).id,
        "payment_method": payment,
        "lines": list(lines),
    }
    return client.post("/api/v1/sales", json=body, headers=headers)
