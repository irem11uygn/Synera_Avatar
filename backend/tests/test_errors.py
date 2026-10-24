"""API hata biçimi (api.md §3)."""

from decimal import Decimal

from fastapi.testclient import TestClient

from app.errors import LotBlocked
from app.main import create_app


def test_domain_error_uses_api_format_and_keeps_decimals_as_text():
    app = create_app()

    @app.get("/_test/bloke")
    def blocked():
        raise LotBlocked(
            "SUC-2026-045 lotu bloke; satılamaz.", lot_no="SUC-2026-045", available=Decimal("1.50")
        )

    response = TestClient(app).get("/_test/bloke")

    assert response.status_code == 409
    assert response.json() == {
        "error": {
            "code": "LOT_BLOCKED",
            "message": "SUC-2026-045 lotu bloke; satılamaz.",
            "details": {"lot_no": "SUC-2026-045", "available": "1.50"},
        }
    }


def test_request_validation_error_uses_same_format():
    app = create_app()

    @app.get("/_test/miktar")
    def quantity(miktar: int):
        return {"miktar": miktar}

    response = TestClient(app).get("/_test/miktar", params={"miktar": "abc"})

    body = response.json()["error"]
    assert response.status_code == 422
    assert body["code"] == "VALIDATION_ERROR"
    assert body["details"]["fields"][0]["field"] == "query.miktar"
