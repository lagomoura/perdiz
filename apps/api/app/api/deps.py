"""Common FastAPI dependencies.

Auth dependencies are stubs for now — full implementation lands with the auth
feature PR. They already enforce 'default deny' on endpoints that declare them.
"""
from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import AsyncSessionLocal
from app.exceptions import AuthError


async def get_db() -> AsyncIterator[AsyncSession]:
    async with AsyncSessionLocal() as session:
        yield session


DbSession = Annotated[AsyncSession, Depends(get_db)]


async def current_user() -> None:
    # TODO(auth): extract bearer, verify JWT, load user, check status.
    raise AuthError()


async def current_verified_user() -> None:
    # TODO(auth): current_user + check email_verified_at is not null.
    raise AuthError()


def require_role(_role: str):  # type: ignore[no-untyped-def]
    async def _dep() -> None:
        # TODO(auth): current_user + role check. On admin endpoints, raise 404
        # via NotFoundError to avoid enumeration (see docs/architecture/security.md).
        raise AuthError()

    return _dep
