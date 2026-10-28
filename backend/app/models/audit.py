"""Denetim günlüğü, sistem ayarları, e-posta giden kutusu ve alarm abonelikleri."""

from datetime import datetime

from sqlalchemy import BigInteger, ForeignKey, Integer, LargeBinary, String, Text
from sqlalchemy.dialects import mysql
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base
from app.models.enums import AlertKind, MailStatus, Severity
from app.models.types import TIMESTAMP, IdMixin, db_enum, utcnow


class AuditEvent(IdMixin, Base):
    """Kim, ne zaman, ne yaptı. Yalnız eklenir; değiştirilmez, silinmez."""

    __tablename__ = "audit_events"

    created_at: Mapped[datetime] = mapped_column(TIMESTAMP, default=utcnow, index=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    username: Mapped[str | None] = mapped_column(String(50), index=True)  # hatalı girişte yazılan ad
    severity: Mapped[Severity] = mapped_column(db_enum(Severity), default=Severity.BILGI)
    action: Mapped[str] = mapped_column(String(40))
    message: Mapped[str] = mapped_column(String(500))
    ref_type: Mapped[str | None] = mapped_column(String(30))
    ref_id: Mapped[int | None] = mapped_column(BigInteger)
    client: Mapped[str | None] = mapped_column(String(64))  # istemci adresi (girişte)


class AppSetting(Base):
    """Yöneticinin değiştirebildiği ayarlar (alarm eşikleri); değer metin olarak tutulur."""

    __tablename__ = "app_settings"

    key: Mapped[str] = mapped_column(String(50), primary_key=True)
    value: Mapped[str] = mapped_column(String(200))
    updated_at: Mapped[datetime] = mapped_column(TIMESTAMP, default=utcnow)
    updated_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"))


class MailMessage(IdMixin, Base):
    """Giden kutusu: e-posta önce buraya yazılır; e-posta sunucusu tanımlıysa arka planda gönderilir."""

    __tablename__ = "mail_outbox"

    created_at: Mapped[datetime] = mapped_column(TIMESTAMP, default=utcnow)
    created_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    kind: Mapped[str] = mapped_column(String(20))  # ALARM | RAPOR
    recipients: Mapped[str] = mapped_column(String(1000))  # virgülle ayrılmış adresler
    subject: Mapped[str] = mapped_column(String(200))
    body: Mapped[str] = mapped_column(Text)
    status: Mapped[MailStatus] = mapped_column(db_enum(MailStatus), default=MailStatus.KUYRUKTA)
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    sent_at: Mapped[datetime | None] = mapped_column(TIMESTAMP)
    last_error: Mapped[str | None] = mapped_column(String(500))
    alert_id: Mapped[int | None] = mapped_column(ForeignKey("alerts.id"))
    html: Mapped[str | None] = mapped_column(Text)  # boşsa düz metin gövdeden üretilir
    attachment_name: Mapped[str | None] = mapped_column(String(200))
    attachment_mime: Mapped[str | None] = mapped_column(String(100))
    attachment: Mapped[bytes | None] = mapped_column(LargeBinary().with_variant(mysql.MEDIUMBLOB(), "mysql"))
    # Aynı alarmın aynı alıcıya ikinci kez gitmemesi: "ALERT:<alarm no>:<adres>" (rapor e-postasında boş).
    dedup_key: Mapped[str | None] = mapped_column(String(150), unique=True)


class AlertSubscription(Base):
    """Kullanıcının alarm türü aboneliği. Kayıt yoksa rolün varsayılanı geçerlidir
    (services/subscriptions.py)."""

    __tablename__ = "alert_subscriptions"

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), primary_key=True)
    alert_type: Mapped[AlertKind] = mapped_column(db_enum(AlertKind), primary_key=True)
    enabled: Mapped[bool] = mapped_column(default=True)
    updated_at: Mapped[datetime] = mapped_column(TIMESTAMP, default=utcnow)
