"""Alarm merkezi: liste, zil özeti, okundu işaretleme, kuralları çalıştırma, eşikler, e-posta abonelikleri."""

from fastapi import APIRouter
from pydantic import BaseModel, Field
from sqlalchemy import func, select

from app.api.deps import AdminUser, Db, WebUser
from app.api.fields import UtcDateTime
from app.models import Alert, User
from app.models.enums import AlertKind, Severity
from app.services import alarms, app_settings, audit, subscriptions
from app.services.lookups import get_or_404

router = APIRouter(prefix="/alerts", tags=["alarm"])
settings_router = APIRouter(prefix="/settings", tags=["alarm"])


class AlertOut(BaseModel):
    id: int
    kind: AlertKind
    kind_label: str
    severity: Severity
    ref_type: str
    ref_id: int
    message: str
    created_at: UtcDateTime
    acknowledged_at: UtcDateTime | None
    acknowledged_by_name: str | None
    can_acknowledge: bool


class AlertSummaryOut(BaseModel):
    open_total: int
    open_critical: int
    open_warning: int
    latest: list[AlertOut]


class RuleRunOut(BaseModel):
    created: list[AlertOut]
    checked: dict[str, int]
    notes: list[str]


class ThresholdsOut(BaseModel):
    yield_z: str
    price_increase_pct: str
    failed_logins: str


class ThresholdsIn(BaseModel):
    yield_z: str | None = Field(default=None, max_length=20)
    price_increase_pct: str | None = Field(default=None, max_length=20)
    failed_logins: str | None = Field(default=None, max_length=20)


def alert_out(db: Db, user: User, alert: Alert) -> AlertOut:
    by = db.get(User, alert.acknowledged_by) if alert.acknowledged_by else None
    return AlertOut(
        id=alert.id,
        kind=alert.kind,
        kind_label=alarms.KIND_LABEL[alert.kind],
        severity=alert.severity,
        ref_type=alert.ref_type,
        ref_id=alert.ref_id,
        message=alert.message,
        created_at=alert.created_at,
        acknowledged_at=alert.acknowledged_at,
        acknowledged_by_name=by.full_name if by else None,
        can_acknowledge=alert.acknowledged_at is None and alarms.can_acknowledge(user, alert),
    )


@router.get("", response_model=list[AlertOut])
def list_alerts(
    db: Db, user: WebUser, only_open: bool = False, severity: Severity | None = None, limit: int = 300
) -> list[AlertOut]:
    query = (
        select(Alert)
        .where(Alert.kind.in_(alarms.visible_kinds(user)))
        .order_by(Alert.id.desc())
        .limit(min(max(limit, 1), 1000))
    )
    if only_open:
        query = query.where(Alert.acknowledged_at.is_(None))
    if severity:
        query = query.where(Alert.severity == severity)
    return [alert_out(db, user, a) for a in db.scalars(query)]


class SubscriptionOut(BaseModel):
    alert_type: AlertKind
    label: str
    enabled: bool
    is_default: bool  # kullanıcı değiştirmedi, rolün varsayılanı


class SubscriptionsOut(BaseModel):
    email: str | None  # boşsa e-posta gitmez (yönetici kullanıcı kartına yazar)
    subscriptions: list[SubscriptionOut]


class SubscriptionIn(BaseModel):
    alert_type: AlertKind
    enabled: bool


class SubscriptionsIn(BaseModel):
    subscriptions: list[SubscriptionIn] = Field(min_length=1, max_length=50)


def _subscriptions_out(db: Db, user: User) -> SubscriptionsOut:
    return SubscriptionsOut(
        email=user.email,
        subscriptions=[
            SubscriptionOut(
                alert_type=kind, label=alarms.KIND_LABEL[kind], enabled=enabled, is_default=default
            )
            for kind, enabled, default in subscriptions.subscriptions(db, user)
        ],
    )


@router.get("/subscriptions", response_model=SubscriptionsOut)
def my_subscriptions(db: Db, user: WebUser) -> SubscriptionsOut:
    """Kendi alarm e-postası aboneliklerim (değiştirmediklerim rolün varsayılanı)."""
    return _subscriptions_out(db, user)


@router.put("/subscriptions", response_model=SubscriptionsOut)
def update_subscriptions(body: SubscriptionsIn, db: Db, user: WebUser) -> SubscriptionsOut:
    """Yalnız gönderilen türler değişir; görülemeyen tür (ör. hatalı giriş, yönetici dışı) 422."""
    changes = subscriptions.update(db, user, [(s.alert_type, s.enabled) for s in body.subscriptions])
    if changes:
        audit.log(db, "ABONELIK", "Alarm e-postası abonelikleri: " + "; ".join(changes), user=user)
    return _subscriptions_out(db, user)


@router.get("/summary", response_model=AlertSummaryOut)
def summary(db: Db, user: WebUser) -> AlertSummaryOut:
    """Üst çubuktaki zil: açık alarm sayıları ve son beş açık alarm."""
    open_alerts = Alert.acknowledged_at.is_(None) & Alert.kind.in_(alarms.visible_kinds(user))
    counts = dict(
        db.execute(select(Alert.severity, func.count()).where(open_alerts).group_by(Alert.severity)).all()
    )
    latest = db.scalars(select(Alert).where(open_alerts).order_by(Alert.id.desc()).limit(5))
    return AlertSummaryOut(
        open_total=sum(counts.values()),
        open_critical=counts.get(Severity.KRITIK, 0),
        open_warning=counts.get(Severity.UYARI, 0),
        latest=[alert_out(db, user, a) for a in latest],
    )


@router.post("/{alert_id}/ack", response_model=AlertOut)
def acknowledge(alert_id: int, db: Db, user: WebUser) -> AlertOut:
    alert = get_or_404(db, Alert, alert_id, "Alarm")
    return alert_out(db, user, alarms.acknowledge(db, user, alert))


@router.post("/ack-all", response_model=list[AlertOut])
def acknowledge_all(db: Db, user: WebUser) -> list[AlertOut]:
    """Kullanıcının okundu işaretleyebildiği bütün açık alarmlar."""
    open_alerts = db.scalars(
        select(Alert).where(Alert.acknowledged_at.is_(None), Alert.kind.in_(alarms.visible_kinds(user)))
    ).all()
    done = [alarms.acknowledge(db, user, a) for a in open_alerts if alarms.can_acknowledge(user, a)]
    return [alert_out(db, user, a) for a in done]


@router.post("/run-rules", response_model=RuleRunOut)
def run_rules(db: Db, user: AdminUser) -> RuleRunOut:
    run = alarms.run_rules(db, user)
    audit.log(
        db,
        "KURAL",
        f"Alarm kuralları elle çalıştırıldı: {len(run.created)} yeni alarm "
        f"({', '.join(f'{k} {v} kayıt' for k, v in run.checked.items())}).",
        user=user,
    )
    return RuleRunOut(
        created=[alert_out(db, user, a) for a in run.created], checked=run.checked, notes=run.notes
    )


@settings_router.get("/alarm-thresholds", response_model=ThresholdsOut)
def get_thresholds(db: Db, _: WebUser) -> ThresholdsOut:
    return ThresholdsOut(**app_settings.thresholds(db).as_dict())


@settings_router.put("/alarm-thresholds", response_model=ThresholdsOut)
def put_thresholds(body: ThresholdsIn, db: Db, user: AdminUser) -> ThresholdsOut:
    values = {k: v for k, v in body.model_dump().items() if v is not None}
    current, changes = app_settings.update_thresholds(db, user, values)
    if changes:
        audit.log(
            db, "AYAR", "Alarm eşikleri değişti: " + "; ".join(changes), user=user, severity=Severity.UYARI
        )
    return ThresholdsOut(**current.as_dict())
