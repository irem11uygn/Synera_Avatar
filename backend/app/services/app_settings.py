"""Yöneticinin değiştirebildiği alarm eşikleri; tabloda kayıt yoksa varsayılan geçerlidir."""

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.errors import InvalidInput
from app.models import AppSetting, User
from app.models.types import utcnow


@dataclass(frozen=True)
class Thresholds:
    yield_z: Decimal  # |z| bundan büyükse verim sapması alarmı
    price_increase_pct: Decimal  # alış fiyatı bir önceki alışa göre % bundan fazla artarsa
    failed_logins: int  # art arda bu kadar hatalı giriş kritik alarm

    def as_dict(self) -> dict[str, str]:
        return {
            "yield_z": str(self.yield_z),
            "price_increase_pct": str(self.price_increase_pct),
            "failed_logins": str(self.failed_logins),
        }


DEFAULTS = Thresholds(yield_z=Decimal("2.0"), price_increase_pct=Decimal("10"), failed_logins=3)
LIMITS = {
    "yield_z": (Decimal("0.5"), Decimal("10")),
    "price_increase_pct": (Decimal("0"), Decimal("500")),
    "failed_logins": (Decimal("2"), Decimal("20")),
}
LABELS = {
    "yield_z": "Verim z-skoru eşiği",
    "price_increase_pct": "Alış fiyatı artış eşiği (%)",
    "failed_logins": "Art arda hatalı giriş sayısı",
}


def thresholds(session: Session) -> Thresholds:
    stored = {row.key: row.value for row in session.scalars(select(AppSetting))}
    defaults = DEFAULTS.as_dict()
    values = {key: stored.get(f"alarm.{key}", default) for key, default in defaults.items()}
    return Thresholds(
        yield_z=Decimal(values["yield_z"]),
        price_increase_pct=Decimal(values["price_increase_pct"]),
        failed_logins=int(values["failed_logins"]),
    )


def update_thresholds(session: Session, user: User, values: dict[str, str]) -> tuple[Thresholds, list[str]]:
    """Eşikleri doğrular ve kaydeder; değişen eşiklerin açıklamasını döner (denetim günlüğü için)."""
    current = thresholds(session).as_dict()
    changes: list[str] = []
    for key, raw in values.items():
        if key not in LIMITS:
            raise InvalidInput(f"Bilinmeyen ayar: {key}.")
        try:
            value = Decimal(str(raw).replace(",", "."))
        except InvalidOperation:
            raise InvalidInput(f"{LABELS[key]} sayı olmalı.") from None
        low, high = LIMITS[key]
        if not low <= value <= high:
            raise InvalidInput(f"{LABELS[key]} {low} ile {high} arasında olmalı.")
        if key == "failed_logins" and value != value.to_integral_value():
            raise InvalidInput(f"{LABELS[key]} tam sayı olmalı.")
        text = str(int(value)) if key == "failed_logins" else str(value.normalize())
        if Decimal(text) == Decimal(current[key]):
            continue
        row = session.get(AppSetting, f"alarm.{key}")
        if row is None:
            session.add(AppSetting(key=f"alarm.{key}", value=text, updated_by=user.id))
        else:
            row.value, row.updated_at, row.updated_by = text, utcnow(), user.id
        changes.append(f"{LABELS[key]}: {current[key]} → {text}")
    session.flush()
    return thresholds(session), changes
