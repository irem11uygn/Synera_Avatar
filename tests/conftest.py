"""Uçtan uca kabul testleri: çalışan sisteme gerçek HTTP istekleriyle bağlanır (T-23).

Sunucu birim testlerinden farkı: veritabanı geri alınmaz, istekler ağ üzerinden gider, sistem
`docker compose up` ile kurulmuş hâliyle (demo profili) sınanır. Yalnız standart kütüphane kullanılır.
Çalıştırma: `sh scripts/kabul_testleri.sh` (sistemi ayrı bir kopyada sıfırdan kurar, testleri koşar, siler).
"""

import json
import os
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any

import pytest

BASE = os.environ.get("AVATAR_API_URL", "http://localhost:8000/api/v1").rstrip("/")


@dataclass
class Response:
    status: int
    body: Any
    headers: dict[str, str]
    seconds: float

    @property
    def code(self) -> str | None:
        return (self.body or {}).get("error", {}).get("code") if isinstance(self.body, dict) else None


class Api:
    def __init__(self, token: str | None = None) -> None:
        self.token = token

    def request(self, method: str, path: str, body: Any = None) -> Response:
        data = None if body is None else json.dumps(body).encode("utf-8")
        request = urllib.request.Request(f"{BASE}{path}", data=data, method=method)
        request.add_header("Accept", "application/json")
        if data is not None:
            request.add_header("Content-Type", "application/json")
        if self.token:
            request.add_header("Authorization", f"Bearer {self.token}")
        started = time.perf_counter()
        try:
            with urllib.request.urlopen(request, timeout=30) as raw:
                status, payload, headers = raw.status, raw.read(), dict(raw.headers)
        except urllib.error.HTTPError as error:
            status, payload, headers = error.code, error.read(), dict(error.headers)
        seconds = time.perf_counter() - started
        text = payload.decode("utf-8-sig")
        try:
            parsed: Any = json.loads(text) if text else None
        except json.JSONDecodeError:
            parsed = text
        return Response(status, parsed, headers, seconds)

    def get(self, path: str) -> Response:
        return self.request("GET", path)

    def post(self, path: str, body: Any = None) -> Response:
        return self.request("POST", path, body if body is not None else {})

    def put(self, path: str, body: Any) -> Response:
        return self.request("PUT", path, body)

    def ok(self, method: str, path: str, body: Any = None, status: int = 200) -> Any:
        response = self.request(method, path, body)
        assert response.status == status, f"{method} {path}: HTTP {response.status} {response.body}"
        return response.body


def _login(username: str, password: str) -> Api:
    response = Api().post("/auth/login", {"username": username, "password": password})
    assert response.status == 200, response.body
    return Api(response.body["token"])


@pytest.fixture(scope="session", autouse=True)
def system_ready() -> None:
    """Sistem ayağa kalkana kadar bekler (en çok 120 sn)."""
    deadline = time.time() + 120
    while time.time() < deadline:
        try:
            response = Api().get("/health")
            if response.status == 200 and response.body.get("status") == "ok":
                return
        except OSError:
            pass
        time.sleep(2)
    pytest.fail(f"Sistem 120 saniyede hazır olmadı: {BASE}/health")


@pytest.fixture(scope="session")
def admin() -> Api:
    return _login("yonetici", "yonetici123")


@pytest.fixture(scope="session")
def seller() -> Api:
    return _login("satis1", "satis123")


@pytest.fixture(scope="session")
def refs(admin: Api) -> dict[str, dict[str, int]]:
    """Kodlardan kimliklere: ürün, cari, depo, reçete."""
    return {
        "product": {p["code"]: p["id"] for p in admin.ok("GET", "/products")},
        "partner": {p["code"]: p["id"] for p in admin.ok("GET", "/partners")},
        "warehouse": {w["code"]: w["id"] for w in admin.ok("GET", "/warehouses")},
        "recipe": {r["code"]: r["id"] for r in admin.ok("GET", "/cutting-recipes")},
    }


@pytest.fixture(scope="session")
def run_id() -> str:
    """Bu çalıştırmada açılan lotların ve belgelerin eki (aynı sisteme tekrar koşulabilsin)."""
    return time.strftime("%H%M%S")
