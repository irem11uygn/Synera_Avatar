"""İş kuralı hataları: sabit kod + Türkçe mesaj; API bunları api.md §3 biçimine çevirir."""

from typing import Any


class DomainError(Exception):
    code = "DOMAIN_ERROR"
    http_status = 409

    def __init__(self, message: str, **details: Any) -> None:
        super().__init__(message)
        self.message = message
        self.details = details


class InvalidInput(DomainError):
    code = "VALIDATION_ERROR"
    http_status = 422


class AmountMismatchNoteRequired(DomainError):
    code = "AMOUNT_MISMATCH_NOTE_REQUIRED"
    http_status = 422


class Unauthorized(DomainError):
    code = "UNAUTHORIZED"
    http_status = 401


class Forbidden(DomainError):
    code = "FORBIDDEN"
    http_status = 403


class NotFound(DomainError):
    code = "NOT_FOUND"
    http_status = 404


class InsufficientStock(DomainError):
    code = "INSUFFICIENT_STOCK"


class LotBlocked(DomainError):
    code = "LOT_BLOCKED"


class WeightImbalance(DomainError):
    code = "WEIGHT_IMBALANCE"


class InvalidState(DomainError):
    code = "INVALID_STATE"


class DuplicateLotNo(DomainError):
    code = "DUPLICATE_LOT_NO"
