"""JWT access tokens + opaque refresh tokens (with SHA-256 hash storage)."""
from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from typing import TypedDict
from uuid import uuid4

from jose import JWTError, jwt

from app.config import settings
from app.exceptions import AuthError

_ALG = "HS256"
_ISSUER = "perdiz-api"
_AUDIENCE = "perdiz-web"


class AccessTokenPayload(TypedDict):
    sub: str
    role: str
    iat: int
    exp: int
    jti: str
    iss: str
    aud: str


def create_access_token(user_id: str, role: str) -> str:
    now = datetime.now(tz=timezone.utc)
    payload: AccessTokenPayload = {
        "sub": user_id,
        "role": role,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(seconds=settings.jwt_access_ttl_seconds)).timestamp()),
        "jti": uuid4().hex,
        "iss": _ISSUER,
        "aud": _AUDIENCE,
    }
    return jwt.encode(dict(payload), settings.jwt_secret, algorithm=_ALG)


def decode_access_token(token: str) -> AccessTokenPayload:
    secrets_to_try: list[str] = [settings.jwt_secret]
    if settings.jwt_secret_next:
        secrets_to_try.append(settings.jwt_secret_next)
    last_error: JWTError | None = None
    for sec in secrets_to_try:
        try:
            return jwt.decode(  # type: ignore[return-value]
                token,
                sec,
                algorithms=[_ALG],
                audience=_AUDIENCE,
                issuer=_ISSUER,
            )
        except JWTError as e:
            last_error = e
            continue
    raise AuthError("Token inválido o expirado.") from last_error


def sha256_hex(plain: str) -> str:
    return hashlib.sha256(plain.encode("utf-8")).hexdigest()


def generate_refresh_token_plain() -> str:
    return secrets.token_urlsafe(48)


def hash_refresh_token(plain: str) -> str:
    return sha256_hex(plain)


def refresh_expires_at() -> datetime:
    return datetime.now(tz=timezone.utc) + timedelta(seconds=settings.jwt_refresh_ttl_seconds)


def generate_email_verification_token() -> tuple[str, str, datetime]:
    """Return (plain, hashed, expires_at). Plain goes in the email link."""
    plain = secrets.token_urlsafe(32)
    expires = datetime.now(tz=timezone.utc) + timedelta(hours=24)
    return plain, sha256_hex(plain), expires
