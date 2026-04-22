"""Email verification token repository."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.email_verification_token import EmailVerificationToken


async def create(
    db: AsyncSession, *, user_id: str, token_hash: str, expires_at: datetime
) -> EmailVerificationToken:
    token = EmailVerificationToken(user_id=user_id, token_hash=token_hash, expires_at=expires_at)
    db.add(token)
    await db.flush()
    await db.refresh(token)
    return token


async def get_by_hash(db: AsyncSession, token_hash: str) -> EmailVerificationToken | None:
    result = await db.execute(
        select(EmailVerificationToken).where(EmailVerificationToken.token_hash == token_hash)
    )
    return result.scalar_one_or_none()
