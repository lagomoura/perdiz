"""Common FastAPI dependencies."""

from __future__ import annotations

from collections.abc import AsyncIterator, Awaitable, Callable
from typing import Annotated

from fastapi import Depends, Header
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import AsyncSessionLocal
from app.exceptions import (
    AccountSuspended,
    AuthError,
    AuthorizationError,
    EmailNotVerified,
    NotFoundError,
)
from app.models.user import User
from app.repositories import users as users_repo
from app.services.auth.tokens import decode_access_token


async def get_db() -> AsyncIterator[AsyncSession]:
    async with AsyncSessionLocal() as session:
        yield session


DbSession = Annotated[AsyncSession, Depends(get_db)]


async def current_user(
    db: DbSession,
    authorization: Annotated[str | None, Header()] = None,
) -> User:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise AuthError()
    token = authorization[7:].strip()
    if not token:
        raise AuthError()
    payload = decode_access_token(token)
    user_id = payload.get("sub")
    if not isinstance(user_id, str):
        raise AuthError()
    user = await users_repo.get_by_id(db, user_id)
    if user is None:
        raise AuthError()
    if user.status == "suspended":
        raise AccountSuspended()
    return user


CurrentUser = Annotated[User, Depends(current_user)]


async def current_verified_user(user: CurrentUser) -> User:
    if user.email_verified_at is None:
        raise EmailNotVerified()
    return user


CurrentVerifiedUser = Annotated[User, Depends(current_verified_user)]


def require_role(role: str) -> Callable[[User], Awaitable[User]]:
    async def _dep(user: CurrentUser) -> User:
        if user.role != role:
            # Admin endpoints return 404 to avoid enumeration
            # (see docs/architecture/security.md).
            if role == "admin":
                raise NotFoundError()
            raise AuthorizationError()
        return user

    return _dep
