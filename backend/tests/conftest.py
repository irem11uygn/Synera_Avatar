"""Test ortamı: ayrı test veritabanı, temiz şema, test başına geri alınan işlem."""

import os
from collections.abc import Callable, Iterator
from decimal import Decimal

import pytest

# Testler geliştirme/demo verisine dokunmasın: uygulama içe aktarılmadan ÖNCE test veritabanına yönlendir.
if not os.environ.get("TEST_DATABASE_URL"):
    pytest.exit(
        "TEST_DATABASE_URL tanımlı değil; testleri 'docker compose run --rm api pytest' ile çalıştırın.", 2
    )
os.environ["DATABASE_URL"] = os.environ["TEST_DATABASE_URL"]

from alembic import command  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import Engine, text  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402

from app.api.deps import get_db  # noqa: E402
from app.config import get_settings  # noqa: E402
from app.db import get_engine  # noqa: E402
from app.main import create_app  # noqa: E402
from app.models import Lot, Product, StockMovement, Warehouse  # noqa: E402
from app.models.enums import DocType, LotOrigin, MovementType  # noqa: E402
from app.seed import load_profile  # noqa: E402
from app.services.auth import limiter  # noqa: E402
from tests.helpers import alembic_config, by_code  # noqa: E402


@pytest.fixture(scope="session")
def engine() -> Engine:
    """Test veritabanını boşaltır, göçleri baştan uygular ve 'base' örnek kayıtlarını yükler."""
    engine = get_engine()
    with engine.begin() as conn:
        conn.execute(text("SET FOREIGN_KEY_CHECKS = 0"))
        for (table,) in conn.execute(text("SHOW TABLES")).all():
            conn.execute(text(f"DROP TABLE `{table}`"))
        conn.execute(text("SET FOREIGN_KEY_CHECKS = 1"))
    command.upgrade(alembic_config(), "head")
    with Session(engine) as session, session.begin():
        load_profile(session, get_settings().seed_dir, "base")
    return engine


@pytest.fixture(autouse=True)
def _login_limiter() -> Iterator[None]:
    """Hatalı giriş sayacı süreç belleğinde tutulur; testler birbirini etkilemesin."""
    limiter.reset()
    yield
    limiter.reset()


@pytest.fixture
def session(engine: Engine) -> Iterator[Session]:
    """Her test kendi işleminde çalışır; sonunda her şey geri alınır."""
    with engine.connect() as conn:
        transaction = conn.begin()
        session = Session(bind=conn, join_transaction_mode="create_savepoint")
        try:
            yield session
        finally:
            session.close()
            transaction.rollback()


@pytest.fixture
def client(session: Session) -> TestClient:
    """API istemcisi; istekler testin geri alınan işlemi içinde çalışır, kalıcı veri bırakmaz.

    Her istek kendi kayıt noktasında (savepoint) yürür: hata verirse yalnız o isteğin yazdıkları
    geri alınır — canlıdaki "istek başına tek işlem" davranışının aynısı (NFR-003).
    """
    app = create_app()

    def test_db() -> Iterator[Session]:
        request = session.begin_nested()
        try:
            yield session
            session.flush()
            request.commit()
        except Exception:
            request.rollback()
            raise

    app.dependency_overrides[get_db] = test_db
    return TestClient(app)


@pytest.fixture
def make_lot(session: Session) -> Callable[..., Lot]:
    def _make(
        lot_no: str = "TEST-LOT-1", product_code: str = "ET", qty: str = "10", value: str = "97.00"
    ) -> Lot:
        lot = Lot(
            lot_no=lot_no,
            product_id=by_code(session, Product, product_code).id,
            origin=LotOrigin.ALIS,
            initial_qty=Decimal(qty),
            initial_value=Decimal(value),
            unit_cost=Decimal(value) / Decimal(qty),
            remaining_qty=Decimal(qty),
            remaining_value=Decimal(value),
        )
        session.add(lot)
        session.flush()
        return lot

    return _make


@pytest.fixture
def make_movement(session: Session, make_lot: Callable[..., Lot]) -> Callable[..., StockMovement]:
    def _make() -> StockMovement:
        lot = make_lot()
        movement = StockMovement(
            type=MovementType.ALIS_GIRIS,
            lot_id=lot.id,
            product_id=lot.product_id,
            warehouse_id=by_code(session, Warehouse, "ANA").id,
            qty=lot.initial_qty,
            value=lot.initial_value,
            doc_type=DocType.ALIS,
            doc_id=1,
        )
        session.add(movement)
        session.flush()
        return movement

    return _make
