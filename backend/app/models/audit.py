"""Denetim günlüğü, sistem ayarları ve e-posta giden kutusu."""

from datetime import datetime

from sqlalchemy import BigInteger, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base
from app.models.enums import MailStatus, Severity
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
