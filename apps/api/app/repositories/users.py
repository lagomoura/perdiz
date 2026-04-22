"""User repository — thin DB access layer."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User


async def get_by_email(db: AsyncSession, email: str) -> User | None:
    result = await db.execute(select(User).where(User.email == email, User.deleted_at.is_(None)))
    return result.scalar_one_or_none()


async def get_by_id(db: AsyncSession, user_id: str) -> User | None:
    user = await db.get(User, user_id)
    if user is None or user.deleted_at is not None:
        return None
    return user


async def create(
    db: AsyncSession,
    *,
    email: str,
    password_hash: str | None,
    first_name: str | None,
    last_name: str | None,
) -> User:
    user = User(
        email=email,
        password_hash=password_hash,
        first_name=first_name,
        last_name=last_name,
    )
    db.add(user)
    await db.flush()
    await db.refresh(user)
    return user
