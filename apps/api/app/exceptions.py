"""Domain exception hierarchy + stable error codes.

Every user-facing error must map to a code listed here. Frontend consumes the
code to render localized messages.
"""
from __future__ import annotations

from typing import Any


class AppError(Exception):
    """Base for all application errors."""

    status_code: int = 500
    code: str = "INTERNAL_ERROR"
    default_message: str = "Algo salió mal. Probá de nuevo en unos segundos."

    def __init__(
        self,
        message: str | None = None,
        *,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message or self.default_message)
        self.message = message or self.default_message
        self.details = details or {}


class DomainError(AppError):
    status_code = 400
    code = "DOMAIN_ERROR"


class ValidationError(DomainError):
    status_code = 422
    code = "VALIDATION_ERROR"
    default_message = "Los datos enviados no son válidos."


class BusinessRuleViolation(DomainError):
    status_code = 409
    code = "BUSINESS_RULE_VIOLATION"


class ResourceConflict(DomainError):
    status_code = 409
    code = "RESOURCE_CONFLICT"


class AuthError(AppError):
    status_code = 401
    code = "AUTH_ERROR"
    default_message = "Tu sesión no es válida. Ingresá de nuevo."


class AuthorizationError(AppError):
    """Maps to 404 on admin endpoints to avoid enumeration (see security docs)."""

    status_code = 403
    code = "AUTHZ_FORBIDDEN"
    default_message = "No tenés permiso para hacer esto."


class NotFoundError(AppError):
    status_code = 404
    code = "NOT_FOUND"
    default_message = "No encontramos lo que buscás."


class RateLimitError(AppError):
    status_code = 429
    code = "RATE_LIMIT_EXCEEDED"
    default_message = "Estás yendo muy rápido. Esperá unos segundos."


class ExternalServiceError(AppError):
    status_code = 502
    code = "EXTERNAL_SERVICE_ERROR"
    default_message = "Un servicio externo no está respondiendo."


# Specific auth codes (sub-classes sharing AuthError status).
class InvalidCredentials(AuthError):
    code = "AUTH_INVALID_CREDENTIALS"
    default_message = "Email o password incorrectos."


class EmailNotVerified(AuthError):
    status_code = 403
    code = "AUTH_EMAIL_NOT_VERIFIED"
    default_message = "Necesitás verificar tu email antes de continuar."


class AccountLocked(AuthError):
    code = "AUTH_ACCOUNT_LOCKED"
    default_message = "Demasiados intentos fallidos. Probá en 30 minutos."


class AccountSuspended(AuthError):
    code = "AUTH_ACCOUNT_SUSPENDED"
    default_message = "Tu cuenta está suspendida. Contactá a soporte."


class RefreshInvalid(AuthError):
    code = "AUTH_REFRESH_INVALID"


class RefreshExpired(AuthError):
    code = "AUTH_REFRESH_EXPIRED"


class RefreshReused(AuthError):
    code = "AUTH_REFRESH_REUSED"
