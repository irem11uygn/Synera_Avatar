"""Alarm e-postası abonelikleri.

Kayıt yoksa rolün varsayılanı geçerlidir: yönetici bütün türlere, diğer roller yalnız kendi işini
ilgilendiren türlere abonedir. Kullanıcı tercihini değiştirince (alert_subscriptions) o tür için
varsayılan yerine kendi seçimi kullanılır. Kullanıcının göremediği tür (ör. hatalı giriş alarmı yalnız
yöneticiye görünür) e-postayla da gönderilmez.
"""

from collections.abc import Iterable

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.errors import InvalidInput
from app.models import AlertSubscription, User
from app.models.enums import AlertKind, UserRole
from app.models.types import utcnow

K = AlertKind
R = UserRole

ADMIN_ONLY = frozenset({K.HATALI_GIRIS})  # hangi hesabın denendiği yalnız yöneticiye görünür

ROLE_DEFAULTS: dict[UserRole, frozenset[AlertKind]] = {
    R.YONETICI: frozenset(AlertKind),
    R.KALITE: frozenset(
        {
            K.GERI_CAGIRMA,
            K.GERI_CAGIRMA_IHLALI,
            K.SKT_IHLALI,
            K.BLOKE_SATIS_DENEMESI,
            K.BLOKE_STOK,
            K.VERIM_SAPMASI,
            K.SKT_YAKLASIYOR,
        }
    ),
    R.DEPO: frozenset({K.BLOKE_STOK, K.FIYAT_ARTISI, K.SKT_YAKLASIYOR, K.SAYIM_FARKI}),
    R.URETIM: frozenset({K.VERIM_SAPMASI}),
    R.MAGAZA: frozenset({K.BLOKE_SATIS_DENEMESI, K.SKT_YAKLASIYOR, K.SKT_IHLALI}),
    R.SATIS: frozenset(),  # yalnız telefon kullanır; e-posta almaz
}


def visible_kinds(user: User) -> list[AlertKind]:
    return [kind for kind in AlertKind if user.role == R.YONETICI or kind not in ADMIN_ONLY]


def subscriptions(session: Session, user: User) -> list[tuple[AlertKind, bool, bool]]:
    """Kullanıcının görebildiği her tür için (tür, açık mı, varsayılan mı)."""
    stored = {
        row.alert_type: row.enabled
        for row in session.scalars(select(AlertSubscription).where(AlertSubscription.user_id == user.id))
    }
    defaults = ROLE_DEFAULTS[user.role]
    return [(kind, stored.get(kind, kind in defaults), kind not in stored) for kind in visible_kinds(user)]


def update(session: Session, user: User, changes: Iterable[tuple[AlertKind, bool]]) -> list[str]:
    """Tercihleri kaydeder; değişenlerin açıklamasını döner (denetim günlüğü için)."""
    visible = set(visible_kinds(user))
    current = {kind: enabled for kind, enabled, _ in subscriptions(session, user)}
    described: list[str] = []
    for kind, enabled in changes:
        if kind not in visible:
            raise InvalidInput(
                f"{kind.value} alarmlarına abone olamazsınız (yalnız yönetici).", alert_type=kind
            )
        row = session.get(AlertSubscription, (user.id, kind))
        if row is None:
            session.add(AlertSubscription(user_id=user.id, alert_type=kind, enabled=enabled))
        else:
            row.enabled, row.updated_at = enabled, utcnow()
        if current.get(kind) != enabled:
            described.append(f"{kind.value} {'açıldı' if enabled else 'kapatıldı'}")
    session.flush()
    return described


def subscribers(session: Session, kind: AlertKind) -> list[User]:
    """Bu tür alarm için e-posta alacak aktif kullanıcılar (e-postası tanımlı olanlar)."""
    users = session.scalars(select(User).where(User.active, User.email.is_not(None)).order_by(User.id)).all()
    choices = {
        user_id: enabled
        for user_id, enabled in session.execute(
            select(AlertSubscription.user_id, AlertSubscription.enabled).where(
                AlertSubscription.alert_type == kind
            )
        )
    }
    return [
        user
        for user in users
        if user.email
        and kind in visible_kinds(user)
        and choices.get(user.id, kind in ROLE_DEFAULTS[user.role])
    ]
