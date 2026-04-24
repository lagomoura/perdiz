from __future__ import annotations

import pytest
from app.config import settings
from app.db.session import AsyncSessionLocal
from app.repositories import users as users_repo
from app.services.auth import passwords
from app.services.auth.bootstrap import ensure_admin
from sqlalchemy import text


@pytest.fixture
def _bootstrap_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "bootstrap_admin_email", "owner@example.com")
    monkeypatch.setattr(settings, "bootstrap_admin_password", "StrongPass123")


async def test_ensure_admin_creates_when_missing(_bootstrap_env: None) -> None:
    await ensure_admin()

    async with AsyncSessionLocal() as session:
        user = await users_repo.get_by_email(session, "owner@example.com")
    assert user is not None
    assert user.role == "admin"
    assert user.status == "active"
    assert user.email_verified_at is not None
    assert passwords.verify_password("StrongPass123", user.password_hash)


async def test_ensure_admin_promotes_existing_user(_bootstrap_env: None) -> None:
    async with AsyncSessionLocal() as session:
        await users_repo.create(
            session,
            email="owner@example.com",
            password_hash=passwords.hash_password("OriginalPass9"),
            first_name=None,
            last_name=None,
        )
        await session.commit()

    await ensure_admin()

    async with AsyncSessionLocal() as session:
        user = await users_repo.get_by_email(session, "owner@example.com")
    assert user is not None
    assert user.role == "admin"
    # Password is not rotated on promotion.
    assert passwords.verify_password("OriginalPass9", user.password_hash)
    assert not passwords.verify_password("StrongPass123", user.password_hash)


async def test_ensure_admin_noop_when_already_admin(_bootstrap_env: None) -> None:
    async with AsyncSessionLocal() as session:
        await session.execute(
            text(
                "INSERT INTO users "
                "(id, email, password_hash, role, status, created_at, updated_at) "
                "VALUES (:id, :email, :hash, 'admin', 'active', now(), now())"
            ),
            {
                "id": "01HZZZZZZZZZZZZZZZZZZZZZZZ",
                "email": "owner@example.com",
                "hash": passwords.hash_password("AdminPass123"),
            },
        )
        await session.commit()

    await ensure_admin()  # must not raise

    async with AsyncSessionLocal() as session:
        user = await users_repo.get_by_email(session, "owner@example.com")
    assert user is not None
    assert user.role == "admin"
    assert passwords.verify_password("AdminPass123", user.password_hash)


async def test_ensure_admin_skips_when_not_configured(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "bootstrap_admin_email", "")
    monkeypatch.setattr(settings, "bootstrap_admin_password", "")

    await ensure_admin()

    async with AsyncSessionLocal() as session:
        result = await session.execute(text("SELECT count(*) FROM users"))
    assert result.scalar_one() == 0


async def test_ensure_admin_rejects_weak_password(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "bootstrap_admin_email", "owner@example.com")
    monkeypatch.setattr(settings, "bootstrap_admin_password", "short")

    await ensure_admin()

    async with AsyncSessionLocal() as session:
        user = await users_repo.get_by_email(session, "owner@example.com")
    assert user is None
