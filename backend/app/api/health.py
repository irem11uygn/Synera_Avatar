"""Servis ve veritabanı durumu (GET /api/v1/health)."""

import logging
from typing import Literal

from fastapi import APIRouter, Response, status
from pydantic import BaseModel
from sqlalchemy.exc import SQLAlchemyError

from app import __version__
from app.db import ping_database

logger = logging.getLogger(__name__)

router = APIRouter(tags=["sistem"])


class HealthResponse(BaseModel):
    status: Literal["ok", "degraded"]
    database: Literal["ok", "error"]
    version: str


@router.get("/health", response_model=HealthResponse)
def health(response: Response) -> HealthResponse:
    try:
        ping_database()
    except SQLAlchemyError:
        logger.warning("Sağlık kontrolü: veritabanına ulaşılamadı", exc_info=True)
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return HealthResponse(status="degraded", database="error", version=__version__)
    return HealthResponse(status="ok", database="ok", version=__version__)
