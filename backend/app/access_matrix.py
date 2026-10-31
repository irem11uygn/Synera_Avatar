"""API yetki matrisi: her uç için yöntem, yol, kimlik doğrulama ve izin verilen roller.

Bilgi elle yazılmaz, uygulamanın kendi bağımlılıklarından okunur (require_role kapanışındaki roller); bu
yüzden kodla belge ayrışamaz. Testler (tests/test_access_matrix.py) aynı tabloyla her uca girişsiz ve
yetkisiz rolle istek atıp reddedildiğini doğrular.

Belge üretimi (depo kökünde):
    docker compose run --rm --no-deps api python -m app.access_matrix > docs/guvenlik/api_yetki_matrisi.md
"""

from collections.abc import Iterator
from dataclasses import dataclass

from fastapi import FastAPI
from fastapi.dependencies.models import Dependant
from fastapi.routing import APIRoute

from app.api.deps import current_user
from app.models.enums import UserRole

PUBLIC = {("GET", "/api/v1/health"), ("POST", "/api/v1/auth/login")}


@dataclass(frozen=True)
class RouteRule:
    method: str
    path: str
    name: str
    authenticated: bool
    roles: tuple[UserRole, ...] | None  # None: giriş yapan herkes


def _walk(dependant: Dependant) -> Iterator[Dependant]:
    for dep in dependant.dependencies:
        yield dep
        yield from _walk(dep)


def _roles(dependant: Dependant) -> tuple[UserRole, ...] | None:
    for dep in _walk(dependant):
        call = dep.call
        if getattr(call, "__qualname__", "") == "require_role.<locals>.check" and call.__closure__:
            for cell in call.__closure__:
                value = cell.cell_contents
                if isinstance(value, tuple) and value and all(isinstance(v, UserRole) for v in value):
                    return value
    return None


def _api_routes(routes: list, prefix: str = "") -> Iterator[tuple[str, APIRoute]]:
    for route in routes:
        if isinstance(route, APIRoute):
            yield prefix + route.path, route
        elif inner := getattr(route, "original_router", None):  # include_router ile eklenen yönlendirici
            yield from _api_routes(inner.routes, prefix + route.include_context.prefix)


def route_rules(app: FastAPI) -> list[RouteRule]:
    rules = []
    for path, route in _api_routes(app.routes):
        authenticated = any(dep.call is current_user for dep in _walk(route.dependant))
        for method in sorted(route.methods - {"HEAD", "OPTIONS"}):
            rules.append(RouteRule(method, path, route.name, authenticated, _roles(route.dependant)))
    return sorted(rules, key=lambda r: (r.path, r.method))


ROLE_SHORT = {
    UserRole.YONETICI: "Y",
    UserRole.DEPO: "D",
    UserRole.URETIM: "Ü",
    UserRole.KALITE: "K",
    UserRole.MAGAZA: "M",
    UserRole.SATIS: "S",
}


def markdown(rules: list[RouteRule]) -> str:
    lines = [
        "# API yetki matrisi",
        "",
        "Kaynak koddan üretilir (`python -m app.access_matrix`); elle düzenlemeyin.",
        "Roller: Y yönetici, D depo, Ü üretim, K kalite, M mağaza, S satış (telefon). "
        '"Giriş" = oturum açmış herkes.',
        "",
        "Doğrulama: `tests/test_access_matrix.py` her uca girişsiz istek atar (401 beklenir) ve izinli "
        "olmayan her rolle istek atar (403 beklenir).",
        "",
        "| Yöntem | Yol | Kimlik | İzinli roller |",
        "|---|---|---|---|",
    ]
    for r in rules:
        if not r.authenticated:
            who = "herkese açık"
        elif r.roles is None:
            who = "giriş"
        else:
            who = ", ".join(ROLE_SHORT[role] for role in UserRole if role in r.roles)
        lines.append(f"| {r.method} | `{r.path}` | {'gerekli' if r.authenticated else '—'} | {who} |")
    lines += ["", f"Toplam {len(rules)} uç; herkese açık: {sum(not r.authenticated for r in rules)}."]
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    import sys

    from app.main import create_app

    sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[union-attr]
    sys.stdout.write(markdown(route_rules(create_app())))
