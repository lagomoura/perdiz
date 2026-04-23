"""Shared test helpers for admin endpoints."""

from __future__ import annotations

from app.db.session import AsyncSessionLocal
from app.models.user import User
from httpx import AsyncClient
from sqlalchemy import update


async def register_and_promote_admin(
    client: AsyncClient,
    *,
    email: str = "admin@example.com",
    password: str = "AdminPass123",
) -> str:
    """Register a fresh user, promote to admin via DB, log in, return the
    Bearer access token.
    """
    reg = await client.post(
        "/v1/auth/register",
        json={"email": email, "password": password, "first_name": "Admin", "last_name": "Test"},
    )
    assert reg.status_code == 201, reg.text

    async with AsyncSessionLocal() as s:
        await s.execute(update(User).where(User.email == email).values(role="admin"))
        await s.commit()

    login = await client.post("/v1/auth/login", json={"email": email, "password": password})
    assert login.status_code == 200, login.text
    return str(login.json()["access_token"])


async def register_user(
    client: AsyncClient,
    *,
    email: str = "user@example.com",
    password: str = "UserPass123",
) -> str:
    reg = await client.post(
        "/v1/auth/register",
        json={"email": email, "password": password, "first_name": "User", "last_name": "Test"},
    )
    assert reg.status_code == 201, reg.text
    login = await client.post("/v1/auth/login", json={"email": email, "password": password})
    return str(login.json()["access_token"])


def auth_header(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}
