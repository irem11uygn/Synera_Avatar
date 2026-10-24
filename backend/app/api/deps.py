"""Ortak bağımlılıklar: istek başına tek veritabanı işlemi (NFR-003), oturum ve rol denetimi."""

from collections.abc import Callable, Iterator
from typing import Annotated

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.db import get_sessionmaker
from app.errors import Forbidden, Unauthorized
from app.models import User
from app.models.enums import UserRole
from app.services.auth import user_for_token


def get_db() -> Iterator[Session]:
    """İstek başarılıysa işlem kaydedilir; herhangi bir hatada bütünüyle geri alınır."""
    with get_sessionmaker()() as session:
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise


# scope="function": kayıt (commit) yanıt GÖNDERİLMEDEN önce yapılır. Varsayılanda bu kod yanıttan sonra
# çalışıyordu; istemci "başarılı" yanıtı alıp hemen yeni istek atınca veriyi henüz göremiyordu.
Db = Annotated[Session, Depends(get_db, scope="function")]

bearer = HTTPBearer(auto_error=False)


def current_user(
    session: Db, credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)]
) -> User:
    if credentials is None:
        raise Unauthorized("Oturum açılmamış.")
    user = user_for_token(session, credentials.credentials)
    if user is None:
        raise Unauthorized("Oturum geçersiz veya süresi dolmuş; yeniden giriş yapın.")
    return user


CurrentUser = Annotated[User, Depends(current_user)]


def require_role(*roles: UserRole) -> Callable[[User], User]:
    def check(user: CurrentUser) -> User:
        if user.role not in roles:
            raise Forbidden("Bu işlem için yetkiniz yok.", role=user.role)
        return user

    return check


AdminUser = Annotated[User, Depends(require_role(UserRole.YONETICI))]
