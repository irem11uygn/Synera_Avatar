"""Kullanıcı yönetimi (yalnız yönetici)."""

from fastapi import APIRouter
from pydantic import BaseModel, Field
from sqlalchemy import select

from app.api.auth import UserOut, user_out
from app.api.deps import AdminUser, Db
from app.models import User
from app.models.enums import Severity, UserRole
from app.services import audit
from app.services import users as service
from app.services.lookups import get_or_404

router = APIRouter(prefix="/users", tags=["kullanıcılar"])

ROLE_NAMES = {
    UserRole.YONETICI: "yönetici",
    UserRole.DEPO: "depo",
    UserRole.URETIM: "üretim",
    UserRole.KALITE: "kalite",
    UserRole.MAGAZA: "mağaza",
    UserRole.SATIS: "satış",
}


class UserCreateIn(BaseModel):
    username: str = Field(min_length=3, max_length=50)
    full_name: str = Field(min_length=1, max_length=100)
    role: UserRole
    password: str = Field(min_length=1, max_length=200)
    warehouse_id: int | None = None
    email: str | None = Field(default=None, max_length=120)


class UserUpdateIn(BaseModel):
    full_name: str = Field(min_length=1, max_length=100)
    role: UserRole
    active: bool
    warehouse_id: int | None = None
    email: str | None = Field(default=None, max_length=120)


class UserAdminOut(UserOut):
    active: bool


class ResetPasswordIn(BaseModel):
    new_password: str | None = Field(default=None, max_length=200)  # boşsa geçici şifre üretilir


class ResetPasswordOut(BaseModel):
    temporary_password: str


def _out(db: Db, user: User) -> UserAdminOut:
    return UserAdminOut(**user_out(db, user).model_dump(), active=user.active)


@router.get("", response_model=list[UserAdminOut])
def list_users(db: Db, _: AdminUser) -> list[UserAdminOut]:
    return [_out(db, u) for u in db.scalars(select(User).order_by(User.active.desc(), User.full_name))]


@router.post("", response_model=UserAdminOut, status_code=201)
def create(body: UserCreateIn, db: Db, admin: AdminUser) -> UserAdminOut:
    user = service.create_user(db, **body.model_dump())
    audit.log(
        db,
        "KULLANICI",
        f"Kullanıcı eklendi: {user.username} ({ROLE_NAMES[user.role]})",
        user=admin,
        ref_type="USER",
        ref_id=user.id,
    )
    return _out(db, user)


@router.put("/{user_id}", response_model=UserAdminOut)
def update(user_id: int, body: UserUpdateIn, db: Db, admin: AdminUser) -> UserAdminOut:
    user = get_or_404(db, User, user_id, "Kullanıcı")
    before = (user.role, user.active)
    service.update_user(db, user, acting=admin, **body.model_dump())
    changes = []
    if before[0] != user.role:
        changes.append(f"rol {ROLE_NAMES[before[0]]} → {ROLE_NAMES[user.role]}")
    if before[1] != user.active:
        changes.append("aktifleştirildi" if user.active else "pasifleştirildi")
    audit.log(
        db,
        "KULLANICI",
        f"Kullanıcı değişti: {user.username}" + (f" ({', '.join(changes)})" if changes else ""),
        user=admin,
        severity=Severity.UYARI if changes else Severity.BILGI,
        ref_type="USER",
        ref_id=user.id,
    )
    return _out(db, user)


@router.post("/{user_id}/reset-password", response_model=ResetPasswordOut)
def reset_password(user_id: int, body: ResetPasswordIn, db: Db, admin: AdminUser) -> ResetPasswordOut:
    """Geçici şifre verir; kullanıcı ilk girişte değiştirmek zorundadır, açık oturumları kapanır."""
    user = get_or_404(db, User, user_id, "Kullanıcı")
    password = service.reset_password(db, user, body.new_password)
    audit.log(
        db,
        "SIFRE_SIFIRLANDI",
        f"{user.username} kullanıcısının şifresi sıfırlandı",
        user=admin,
        severity=Severity.UYARI,
        ref_type="USER",
        ref_id=user.id,
    )
    return ResetPasswordOut(temporary_password=password)
