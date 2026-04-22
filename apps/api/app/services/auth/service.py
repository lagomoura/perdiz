"""Orchestration layer for auth operations.

Endpoints delegate to these functions; these functions coordinate repositories
and sub-services. No FastAPI imports here.
"""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions import (
    AccountLocked,
    AccountSuspended,
    BusinessRuleViolation,
    InvalidCredentials,
    RefreshExpired,
    RefreshInvalid,
    RefreshReused,
    ResourceConflict,
    ValidationError,
)
from app.models.user import User
from app.repositories import email_verification_tokens as evt_repo
from app.repositories import refresh_tokens as rt_repo
from app.repositories import users as users_repo
from app.services.auth import emails, lockout, passwords, tokens
from app.utils.ulid import new_ulid


async def register_user(
    db: AsyncSession,
    *,
    email: str,
    password: str,
    first_name: str | None,
    last_name: str | None,
) -> User:
    passwords.validate_password(password)
    hashed = passwords.hash_password(password)
    try:
        user = await users_repo.create(
            db,
            email=email,
            password_hash=hashed,
            first_name=first_name,
            last_name=last_name,
        )
    except IntegrityError as e:
        raise ResourceConflict(
            "Ya existe una cuenta con ese email.", details={"field": "email"}
        ) from e

    plain, token_hash, expires = tokens.generate_email_verification_token()
    await evt_repo.create(db, user_id=user.id, token_hash=token_hash, expires_at=expires)
    await db.commit()
    await emails.send_verification_email(to=user.email, token_plain=plain)
    return user


async def authenticate(
    db: AsyncSession,
    *,
    email: str,
    password: str,
    user_agent: str | None,
    ip: str | None,
) -> tuple[User, str, str]:
    """Return (user, access_token, refresh_token_plain)."""
    if await lockout.is_locked(email):
        raise AccountLocked()

    user = await users_repo.get_by_email(db, email)
    if user is None or not passwords.verify_password(password, user.password_hash):
        await lockout.record_failure(email)
        raise InvalidCredentials()

    if user.status == "suspended":
        raise AccountSuspended()

    await lockout.clear(email)

    access = tokens.create_access_token(user.id, user.role)
    refresh_plain = tokens.generate_refresh_token_plain()
    await rt_repo.create(
        db,
        user_id=user.id,
        token_hash=tokens.hash_refresh_token(refresh_plain),
        family_id=new_ulid(),
        parent_id=None,
        expires_at=tokens.refresh_expires_at(),
        user_agent=user_agent,
        ip=ip,
    )
    await db.commit()
    return user, access, refresh_plain


async def rotate_refresh(
    db: AsyncSession,
    *,
    refresh_plain: str,
    user_agent: str | None,
    ip: str | None,
) -> tuple[User, str, str]:
    """Return (user, access_token, new_refresh_plain). Detects reuse."""
    token_hash = tokens.hash_refresh_token(refresh_plain)
    record = await rt_repo.get_by_hash(db, token_hash)
    if record is None:
        raise RefreshInvalid()

    now = datetime.now(tz=UTC)

    if record.revoked_at is not None:
        # Reuse detected: revoke the whole family.
        await rt_repo.revoke_family(db, record.family_id)
        await db.commit()
        raise RefreshReused()

    if record.expires_at <= now:
        raise RefreshExpired()

    user = await users_repo.get_by_id(db, record.user_id)
    if user is None or user.status != "active":
        raise RefreshInvalid()

    # Rotate: revoke old, issue new with same family_id.
    await rt_repo.revoke(db, record)
    new_plain = tokens.generate_refresh_token_plain()
    await rt_repo.create(
        db,
        user_id=user.id,
        token_hash=tokens.hash_refresh_token(new_plain),
        family_id=record.family_id,
        parent_id=record.id,
        expires_at=tokens.refresh_expires_at(),
        user_agent=user_agent,
        ip=ip,
    )
    access = tokens.create_access_token(user.id, user.role)
    await db.commit()
    return user, access, new_plain


async def logout(db: AsyncSession, *, refresh_plain: str | None) -> None:
    if not refresh_plain:
        return
    record = await rt_repo.get_by_hash(db, tokens.hash_refresh_token(refresh_plain))
    if record is None:
        return
    await rt_repo.revoke_family(db, record.family_id)
    await db.commit()


async def verify_email(db: AsyncSession, *, token_plain: str) -> User:
    token_hash = tokens.sha256_hex(token_plain)
    record = await evt_repo.get_by_hash(db, token_hash)
    if record is None:
        raise ValidationError(
            "El link de verificación no es válido o ya fue usado.",
            details={"field": "token"},
        )
    now = datetime.now(tz=UTC)
    if record.used_at is not None:
        raise ValidationError("Este link ya fue usado.", details={"field": "token"})
    if record.expires_at <= now:
        raise ValidationError("El link venció. Pedí uno nuevo.", details={"field": "token"})
    user = await users_repo.get_by_id(db, record.user_id)
    if user is None:
        raise ValidationError("No encontramos la cuenta.", details={"field": "token"})
    record.used_at = now
    if user.email_verified_at is None:
        user.email_verified_at = now
    await db.commit()
    return user


async def resend_verification(db: AsyncSession, *, user: User) -> None:
    if user.email_verified_at is not None:
        raise BusinessRuleViolation("Tu email ya está verificado.")
    plain, token_hash, expires = tokens.generate_email_verification_token()
    await evt_repo.create(db, user_id=user.id, token_hash=token_hash, expires_at=expires)
    await db.commit()
    await emails.send_verification_email(to=user.email, token_plain=plain)


__all__ = [
    "authenticate",
    "logout",
    "register_user",
    "resend_verification",
    "rotate_refresh",
    "verify_email",
]
