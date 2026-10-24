"""Hataların API yanıtına çevrilmesi (api.md §3): {"error": {"code", "message", "details"}}."""

from decimal import Decimal
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.errors import DomainError, InvalidInput


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


async def _domain_error(_request: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, DomainError)
    return _response(exc.http_status, exc.code, exc.message, exc.details)


async def _validation_error(_request: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, RequestValidationError)
    fields = [{"field": ".".join(str(p) for p in err["loc"]), "problem": err["msg"]} for err in exc.errors()]
    return _response(
        InvalidInput.http_status, InvalidInput.code, "İstekte geçersiz alanlar var.", {"fields": fields}
    )


def register_error_handlers(app: FastAPI) -> None:
    app.add_exception_handler(DomainError, _domain_error)
    app.add_exception_handler(RequestValidationError, _validation_error)
