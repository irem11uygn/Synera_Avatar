"""Hataların API yanıtına çevrilmesi (api.md §3): {"error": {"code", "message", "details"}}."""

import logging
from decimal import Decimal
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError

from app.errors import Conflict, DomainError, InvalidInput

logger = logging.getLogger(__name__)


def _plain(value: Any) -> Any:
    """Ondalıklar metin olarak taşınır (ADR-006); kayan noktalı sayıya çevrilmez."""
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, dict):
        return {key: _plain(item) for key, item in value.items()}
    if isinstance(value, list | tuple):
        return [_plain(item) for item in value]
    return value


def _response(status: int, code: str, message: str, details: dict[str, Any]) -> JSONResponse:
    return JSONResponse(
        status_code=status, content={"error": {"code": code, "message": message, "details": _plain(details)}}
    )


def error_response(exc: DomainError) -> JSONResponse:
    """Hatayı fırlatmadan yanıtlamak için (isteğin işlemi kaydedilsin: ör. hatalı giriş günlüğü)."""
    return _response(exc.http_status, exc.code, exc.message, exc.details)


async def _domain_error(_request: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, DomainError)
    return error_response(exc)


async def _validation_error(_request: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, RequestValidationError)
    fields = [{"field": ".".join(str(p) for p in err["loc"]), "problem": err["msg"]} for err in exc.errors()]
    return _response(
        InvalidInput.http_status, InvalidInput.code, "İstekte geçersiz alanlar var.", {"fields": fields}
    )


async def _integrity_error(request: Request, exc: Exception) -> JSONResponse:
    """Son güvenlik ağı: servis denetimini aşan bir veritabanı kuralı ihlali (ör. aynı anda iki kayıt).
    İşlem zaten geri alınmıştır; kullanıcıya anlaşılır bir mesaj, ayrıntı günlüğe."""
    logger.warning("Veritabanı kuralı ihlali: %s %s", request.method, request.url.path, exc_info=exc)
    return _response(
        Conflict.http_status,
        Conflict.code,
        "Kayıt veritabanı kurallarına takıldı (aynı kayıt zaten olabilir ya da seçilen bir kayıt artık yok). "
        "Bilgileri kontrol edip yeniden deneyin; hiçbir şey kaydedilmedi.",
        {},
    )


async def _unexpected_error(request: Request, exc: Exception) -> JSONResponse:
    logger.error("Beklenmeyen hata: %s %s", request.method, request.url.path, exc_info=exc)
    return _response(
        500,
        "INTERNAL_ERROR",
        "Beklenmeyen bir hata oluştu; işlem kaydedilmedi. Sorun sürerse sistem yöneticisine haber verin.",
        {},
    )


def register_error_handlers(app: FastAPI) -> None:
    app.add_exception_handler(DomainError, _domain_error)
    app.add_exception_handler(RequestValidationError, _validation_error)
    app.add_exception_handler(IntegrityError, _integrity_error)
    app.add_exception_handler(Exception, _unexpected_error)
