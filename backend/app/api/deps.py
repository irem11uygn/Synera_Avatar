"""Ortak bağımlılıklar: istek başına tek veritabanı işlemi (NFR-003), oturum ve rol denetimi."""

from collections.abc import Callable, Iterator
from typing import Annotated

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.db import get_sessionmaker
from app.errors import Forbidden, PasswordChangeRequired, Unauthorized
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
        if user.must_change_password:
            raise PasswordChangeRequired("Devam etmeden önce yeni şifrenizi belirleyin.")
        if user.role not in roles:
            raise Forbidden("Bu işlem için yetkiniz yok.", role=user.role)
        return user

    return check


R = UserRole
WEB_ROLES = (R.YONETICI, R.DEPO, R.URETIM, R.KALITE, R.MAGAZA)

# Rol grupları (orta ölçekli işletme): okuma çoğunlukla bütün web kullanıcılarına açık;
# yazma işlemleri işi yapan birime ve yöneticiye.
AdminUser = Annotated[User, Depends(require_role(R.YONETICI))]
WebUser = Annotated[User, Depends(require_role(*WEB_ROLES))]
StockUser = Annotated[User, Depends(require_role(R.YONETICI, R.DEPO))]
ProductionUser = Annotated[User, Depends(require_role(R.YONETICI, R.URETIM))]
QualityUser = Annotated[User, Depends(require_role(R.YONETICI, R.KALITE))]
StoreUser = Annotated[User, Depends(require_role(R.YONETICI, R.MAGAZA))]
SalesDeskUser = Annotated[
    User, Depends(require_role(R.YONETICI, R.MAGAZA, R.KALITE))
]  # iade, müşteri dağıtımı
PartnerUser = Annotated[
    User, Depends(require_role(R.YONETICI, R.DEPO, R.MAGAZA))
]  # tedarikçi ve müşteri kartı
CountUser = Annotated[User, Depends(require_role(R.YONETICI, R.DEPO, R.SATIS))]  # araç gün sonu sayımı
SellerUser = Annotated[User, Depends(require_role(R.SATIS))]
