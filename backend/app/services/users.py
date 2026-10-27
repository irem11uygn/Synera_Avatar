"""Kullanıcı yönetimi (yalnız yönetici): kullanıcı açma, rol ve depo atama, pasifleştirme, şifre sıfırlama.

Kurallar:
- Kullanıcı adı tekil; küçük harf, rakam, nokta, alt çizgi.
- Saha satış kullanıcısının bir araç deposu olmalı.
- Yönetici kendini pasifleştiremez ve kendi rolünü düşüremez; sistemde en az bir aktif yönetici kalır.
- Şifre sıfırlanınca kullanıcı ilk girişte yenisini belirler; açık oturumları kapanır.
"""

import re
import secrets
import string

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.errors import InvalidInput
from app.models import User, Warehouse
from app.models.enums import UserRole, WarehouseKind
from app.security import hash_password
from app.services.auth import check_new_password, end_all_sessions
from app.services.lookups import get_or_404

USERNAME = re.compile(r"^[a-z0-9._]{3,50}$")


def _check_warehouse(session: Session, role: UserRole, warehouse_id: int | None) -> int | None:
    if role != UserRole.SATIS:
        return None
    if warehouse_id is None:
        raise InvalidInput("Saha satış kullanıcısına bir araç deposu seçilmeli.")
    warehouse = get_or_404(session, Warehouse, warehouse_id, "Depo")
    if warehouse.kind != WarehouseKind.ARAC:
        raise InvalidInput("Saha satış kullanıcısının deposu bir araç deposu olmalı.")
    return warehouse.id


def _active_admins(session: Session) -> int:
    return (
        session.scalar(
            select(func.count()).select_from(User).where(User.role == UserRole.YONETICI, User.active)
        )
        or 0
    )


def create_user(
    session: Session,
    *,
    username: str,
    full_name: str,
    role: UserRole,
    password: str,
    warehouse_id: int | None = None,
) -> User:
    username = username.strip().lower()
    if not USERNAME.match(username):
        raise InvalidInput(
            "Kullanıcı adı 3–50 karakter olmalı; yalnız küçük harf, rakam, nokta ve alt çizgi."
        )
    if session.scalar(select(User.id).where(User.username == username)) is not None:
        raise InvalidInput(f"'{username}' kullanıcı adı zaten kullanılıyor.")
    if not full_name.strip():
        raise InvalidInput("Ad soyad gerekli.")
    check_new_password(password)
    user = User(
        username=username,
        full_name=full_name.strip(),
        role=role,
        password_hash=hash_password(password),
        warehouse_id=_check_warehouse(session, role, warehouse_id),
        must_change_password=True,  # yöneticinin verdiği ilk şifre geçicidir
    )
    session.add(user)
    session.flush()
    return user


def update_user(
    session: Session,
    user: User,
    *,
    acting: User,
    full_name: str,
    role: UserRole,
    active: bool,
    warehouse_id: int | None,
) -> User:
    if not full_name.strip():
        raise InvalidInput("Ad soyad gerekli.")
    if user.id == acting.id and (not active or role != UserRole.YONETICI):
        raise InvalidInput("Kendi hesabınızı pasifleştiremez ya da yönetici rolünü kaldıramazsınız.")
    losing_admin = (
        user.role == UserRole.YONETICI and user.active and (role != UserRole.YONETICI or not active)
    )
    if losing_admin and _active_admins(session) <= 1:
        raise InvalidInput("Sistemde en az bir aktif yönetici kalmalı.")
    user.full_name = full_name.strip()
    user.role = role
    user.warehouse_id = _check_warehouse(session, role, warehouse_id)
    if user.active and not active:
        end_all_sessions(session, user.id)
    user.active = active
    session.flush()
    return user


def reset_password(session: Session, user: User, new_password: str | None = None) -> str:
    """Geçici şifre verir (verilmezse üretilir); kullanıcı ilk girişte değiştirir. Geçici şifre döner."""
    password = new_password or _temporary_password()
    check_new_password(password)
    user.password_hash = hash_password(password)
    user.must_change_password = True
    end_all_sessions(session, user.id)
    session.flush()
    return password


def _temporary_password() -> str:
    letters = "".join(secrets.choice(string.ascii_lowercase) for _ in range(6))
    digits = "".join(secrets.choice(string.digits) for _ in range(4))
    return letters + digits
