"""Bootstrap an admin user at startup from BOOTSTRAP_ADMIN_* settings.

Semantics:
- Both settings missing: no-op.
- Email unknown: create active, email-verified admin with the given password.
- Email exists with role!=admin: promote to admin. Password is not touched.
- Email exists with role==admin: no-op.

Password is never rotated via bootstrap: a leaked .env should not let an
operator silently reset the admin credential. To rotate, use the API.
"""

from __future__ import annotations

from datetime import UTC, datetime

import structlog
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db.session import AsyncSessionLocal
from app.exceptions import ValidationError
from app.models.user import User
from app.repositories import users as users_repo
from app.services.auth import passwords

log = structlog.get_logger(__name__)


async def ensure_admin() -> None:
    email = settings.bootstrap_admin_email.strip()
    password = settings.bootstrap_admin_password
    if not email or not password:
        log.info("bootstrap_admin.skipped", reason="not_configured")
        return

    try:
        passwords.validate_password(password)
    except ValidationError as exc:
        log.error("bootstrap_admin.invalid_password", error=exc.message)
        return

    async with AsyncSessionLocal() as session:
        await _ensure(session, email=email, password=password)


async def _ensure(session: AsyncSession, *, email: str, password: str) -> None:
    existing = await users_repo.get_by_email(session, email)
    if existing is not None:
        if existing.role != "admin":
            existing.role = "admin"
            await session.commit()
            log.info("bootstrap_admin.promoted", email=email)
        else:
            log.info("bootstrap_admin.already_admin", email=email)
        return

    user = User(
        email=email,
        password_hash=passwords.hash_password(password),
        role="admin",
        status="active",
        email_verified_at=datetime.now(UTC),
    )
    session.add(user)
    try:
        await session.commit()
    except IntegrityError:
        # Another worker (uvicorn spawns multiple lifespans) inserted first.
        await session.rollback()
        existing = await users_repo.get_by_email(session, email)
        if existing is None:
            raise
        log.info("bootstrap_admin.already_admin", email=email, race=True)
        return
    log.info("bootstrap_admin.created", email=email)
