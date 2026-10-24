from fastapi.testclient import TestClient
from sqlalchemy.exc import OperationalError

from app import __version__
from app.api import health
from app.main import create_app


def test_health_reports_database_ok():
    """Gerçek veritabanına (Docker'daki MySQL) bağlanır."""
    response = TestClient(create_app()).get("/api/v1/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database": "ok", "version": __version__}


def test_health_reports_degraded_when_database_unreachable(monkeypatch):
    def unreachable():
        raise OperationalError("SELECT 1", {}, Exception("bağlantı yok"))

    monkeypatch.setattr(health, "ping_database", unreachable)

    response = TestClient(create_app()).get("/api/v1/health")

    assert response.status_code == 503
    assert response.json() == {"status": "degraded", "database": "error", "version": __version__}
