"""Erişim denetimi (OWASP A01): bütün uçlar kodun kendi yetki matrisiyle (app/access_matrix.py) sınanır.

- Girişsiz istek: herkese açık iki uç dışındaki her uç 401 vermeli.
- Yetkisiz rol: bir uca izinli olmayan her rol (telefon kullanıcısı dahil) 403 almalı.
İzin verilmeyen istekte iş kuralı hiç çalışmaz (rol denetimi uç fonksiyonundan önce), veri değişmez.
"""

import re

import pytest

from app.access_matrix import PUBLIC, route_rules
from app.main import create_app
from app.models.enums import UserRole
from tests.helpers import auth_header

RULES = route_rules(create_app())
ACCOUNTS = {
    UserRole.YONETICI: ("yonetici", "yonetici123"),
    UserRole.DEPO: ("depo1", "depo1234"),
    UserRole.URETIM: ("uretim1", "uretim123"),
    UserRole.KALITE: ("kalite1", "kalite123"),
    UserRole.MAGAZA: ("magaza1", "magaza123"),
    UserRole.SATIS: ("satis1", "satis123"),
}
SAMPLE = {"code": "sales", "lot_no": "ET-2026-001"}


def _url(path: str) -> str:
    return re.sub(r"\{(\w+)\}", lambda m: SAMPLE.get(m.group(1), "1"), path)


def test_matrix_covers_the_whole_api():
    assert len(RULES) > 80
    assert {(r.method, r.path) for r in RULES if not r.authenticated} == PUBLIC
    assert sum(r.roles is not None for r in RULES) > 70  # rol denetimi okunabildi


def test_every_non_public_endpoint_requires_login(client):
    failures = []
    for rule in RULES:
        if (rule.method, rule.path) in PUBLIC:
            continue
        response = client.request(rule.method, _url(rule.path), json={})
        if response.status_code != 401:
            failures.append((rule.method, rule.path, response.status_code))
    assert failures == []


def test_forged_or_expired_token_is_rejected(client):
    for token in ("uydurma-belirtec", "Bearer", "x" * 43):
        response = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert response.status_code == 401


@pytest.mark.parametrize("role", list(UserRole), ids=lambda r: r.value)
def test_roles_cannot_reach_endpoints_outside_their_job(client, role):
    headers = auth_header(client, *ACCOUNTS[role])
    failures = []
    checked = 0
    for rule in RULES:
        if rule.roles is None or role in rule.roles:
            continue
        checked += 1
        response = client.request(rule.method, _url(rule.path), json={}, headers=headers)
        if response.status_code != 403 or response.json()["error"]["code"] != "FORBIDDEN":
            failures.append((rule.method, rule.path, response.status_code))
    assert failures == []
    if role != UserRole.YONETICI:
        assert checked > 0  # her rolün kapalı olduğu uçlar var
