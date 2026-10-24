"""Giriş ve oturumdaki kullanıcı (api.md §2 — Kimlik)."""

from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.security import HTTPAuthorizationCredentials
from pydantic import BaseModel, Field

from app.api.deps import CurrentUser, Db, bearer
from app.models import User, Warehouse
from app.models.enums import UserRole
from app.services import auth

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


class LoginResponse(BaseModel):
    token: str
    user: UserOut


def _user_out(db: Db, user: User) -> UserOut:
    warehouse = db.get(Warehouse, user.warehouse_id) if user.warehouse_id else None
    return UserOut(
        id=user.id,
        username=user.username,
        full_name=user.full_name,
        role=user.role,
        warehouse_id=user.warehouse_id,
        warehouse_code=warehouse.code if warehouse else None,
    )


@router.post("/login", response_model=LoginResponse)
def login(body: LoginRequest, db: Db) -> LoginResponse:
    token, user = auth.login(db, body.username, body.password)
    return LoginResponse(token=token, user=_user_out(db, user))


@router.get("/me", response_model=UserOut)
def me(user: CurrentUser, db: Db) -> UserOut:
    return _user_out(db, user)


@router.post("/logout", status_code=204)
def logout(
    _: CurrentUser, db: Db, credentials: Annotated[HTTPAuthorizationCredentials, Depends(bearer)]
) -> None:
    auth.logout(db, credentials.credentials)
