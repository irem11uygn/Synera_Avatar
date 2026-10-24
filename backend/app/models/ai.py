"""İş anında kaydedilen YZ tahminleri (data_model.md §2.9, ADR-005)."""

from datetime import datetime
from typing import Any

from sqlalchemy import JSON, BigInteger, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base
from app.models.enums import AiModel, ForecastTarget
from app.models.types import TIMESTAMP, IdMixin, db_enum, utcnow


class AiForecast(IdMixin, Base):
    """Tahmin sonradan değişmez; "tahmin – gerçek – sapma" bu kaydı kullanır."""

    __tablename__ = "ai_forecasts"
    __table_args__ = (Index("ix_ai_forecasts_target", "target_type", "target_id"),)

    model: Mapped[AiModel] = mapped_column(db_enum(AiModel))
    model_version: Mapped[str] = mapped_column(String(40))
    target_type: Mapped[ForecastTarget] = mapped_column(db_enum(ForecastTarget))
    target_id: Mapped[int] = mapped_column(BigInteger)
    features: Mapped[dict[str, Any]] = mapped_column(JSON)
    prediction: Mapped[dict[str, Any]] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP, default=utcnow)
