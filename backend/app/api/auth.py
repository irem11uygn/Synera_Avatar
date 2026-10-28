"""Giriş, oturumdaki kullanıcı, çıkış ve şifre değiştirme (api.md §2 — Kimlik)."""

from typing import Annotated

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from fastapi.security import HTTPAuthorizationCredentials
from pydantic import BaseModel, Field

from app.api.deps import CurrentUser, Db, bearer
from app.api.errors import error_response
from app.errors import TooManyAttempts, Unauthorized
from app.models import User, Warehouse
from app.models.enums import Severity, UserRole
from app.services import alarms, audit, auth

router = APIRouter(prefix="/auth", tags=["kimlik"])


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=50)
    password: str = Field(min_length=1, max_length=200)


class UserOut(BaseModel):
    id: int
    username: str
    full_name: str
    role: UserRole
    warehouse_id: int | None
    warehouse_code: str | None
    must_change_password: bool
    email: str | None


class LoginResponse(BaseModel):
    token: str
    user: UserOut


class ChangePasswordIn(BaseModel):
    current_password: str = Field(min_length=1, max_length=200)
    new_password: str = Field(min_length=1, max_length=200)


def user_out(db: Db, user: User) -> UserOut:
    warehouse = db.get(Warehouse, user.warehouse_id) if user.warehouse_id else None
    return UserOut(
        id=user.id,
        username=user.username,
        full_name=user.full_name,
        role=user.role,
        warehouse_id=user.warehouse_id,
        warehouse_code=warehouse.code if warehouse else None,
        must_change_password=user.must_change_password,
        email=user.email,
    )


@router.post("/login", response_model=LoginResponse, responses={401: {}, 429: {}})
def login(body: LoginRequest, db: Db, request: Request) -> LoginResponse | JSONResponse:
    """Hatalı giriş hata fırlatılmadan yanıtlanır: denetim kaydı ve gerekirse alarm kalıcı olsun
    (fırlatılsaydı isteğin işlemi geri alınırdı). Başarılı girişte alarm kuralları çalışır."""
    # Web arayüzü nginx üzerinden gelir: gerçek adres X-Real-IP'de (nginx istemcinin gönderdiğini ezer).
    client = request.headers.get("x-real-ip") or (request.client.host if request.client else "?")
    try:
        token, user = auth.login(db, body.username, body.password, client)
    except Unauthorized as error:
        alarms.login_failed(db, body.username, client)
        return error_response(error)
    except TooManyAttempts as error:
        audit.log(
            db,
            "GIRIS_ENGELLENDI",
            "Çok fazla hatalı deneme; giriş geçici olarak engellendi: "
            f"'{body.username.strip().lower()[:50]}'",
            username=body.username.strip().lower()[:50],
            severity=Severity.UYARI,
            client=client,
        )
        return error_response(error)
    audit.log(db, "GIRIS", "Oturum açtı", user=user, client=client)
    if user.role != UserRole.SATIS:  # telefon her senkronda giriş yapmaz; kurallar web girişinde yeter
        alarms.run_rules(db, user)
    return LoginResponse(token=token, user=user_out(db, user))


@router.get("/me", response_model=UserOut)
def me(user: CurrentUser, db: Db) -> UserOut:
    return user_out(db, user)


@router.post("/logout", status_code=204)
def logout(
    user: CurrentUser, db: Db, credentials: Annotated[HTTPAuthorizationCredentials, Depends(bearer)]
) -> None:
    auth.logout(db, credentials.credentials)
    audit.log(db, "CIKIS", "Oturumu kapattı", user=user)


@router.post("/change-password", response_model=UserOut)
def change_password(
    body: ChangePasswordIn,
    user: CurrentUser,
    db: Db,
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(bearer)],
) -> UserOut:
    """Kendi şifresini değiştirir; diğer cihazlardaki oturumlar kapanır, bu oturum sürer."""
    auth.change_password(db, user, body.current_password, body.new_password, credentials.credentials)
    audit.log(db, "SIFRE_DEGISTI", "Kendi şifresini değiştirdi; diğer oturumları kapandı", user=user)
    return user_out(db, user)
