from __future__ import annotations

from httpx import AsyncClient
from sqlalchemy import select

from app.db.session import AsyncSessionLocal
from app.models.email_verification_token import EmailVerificationToken
from app.models.user import User
from app.services.auth import tokens as token_service


async def _register_and_get_token_hash(email: str) -> str:
    async with AsyncSessionLocal() as s:
        result = await s.execute(
            select(EmailVerificationToken)
            .join(User, User.id == EmailVerificationToken.user_id)
            .where(User.email == email)
        )
        row = result.scalar_one()
        return row.token_hash


async def test_verify_email_flow(client: AsyncClient) -> None:
    # Register creates the verification token internally.
    await client.post(
        "/v1/auth/register",
        json={
            "email": "verify@ejemplo.com",
            "password": "ValidPass123",
            "first_name": None,
            "last_name": None,
        },
    )
    # We don't know the plain token (it was emailed); for tests we inject one
    # directly via the service to cover the verify endpoint.
    from datetime import datetime

    plain, token_hash, expires = token_service.generate_email_verification_token()
    async with AsyncSessionLocal() as s:
        user = (
            await s.execute(select(User).where(User.email == "verify@ejemplo.com"))
        ).scalar_one()
        s.add(
            EmailVerificationToken(
                user_id=user.id, token_hash=token_hash, expires_at=expires
            )
        )
        await s.commit()

    r = await client.post("/v1/auth/email/verify", json={"token": plain})
    assert r.status_code == 200
    body = r.json()
    assert body["user"]["email_verified"] is True

    async with AsyncSessionLocal() as s:
        user = (
            await s.execute(select(User).where(User.email == "verify@ejemplo.com"))
        ).scalar_one()
        assert user.email_verified_at is not None
        assert user.email_verified_at.tzinfo is not None
        assert isinstance(user.email_verified_at, datetime)


async def test_verify_rejects_invalid_token(client: AsyncClient) -> None:
    r = await client.post("/v1/auth/email/verify", json={"token": "nope"})
    assert r.status_code == 422
    assert r.json()["error"]["code"] == "VALIDATION_ERROR"


async def test_me_requires_auth(client: AsyncClient) -> None:
    r = await client.get("/v1/users/me")
    assert r.status_code == 401


async def test_me_returns_current_user(client: AsyncClient) -> None:
    await client.post(
        "/v1/auth/register",
        json={
            "email": "me@ejemplo.com",
            "password": "ValidPass123",
            "first_name": "Me",
            "last_name": None,
        },
    )
    login = await client.post(
        "/v1/auth/login", json={"email": "me@ejemplo.com", "password": "ValidPass123"}
    )
    access = login.json()["access_token"]
    r = await client.get("/v1/users/me", headers={"Authorization": f"Bearer {access}"})
    assert r.status_code == 200
    assert r.json()["user"]["email"] == "me@ejemplo.com"
