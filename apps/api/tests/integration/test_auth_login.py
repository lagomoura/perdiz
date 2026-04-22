from __future__ import annotations

from httpx import AsyncClient


async def _register(client: AsyncClient, email: str = "login@ejemplo.com") -> None:
    await client.post(
        "/v1/auth/register",
        json={
            "email": email,
            "password": "ValidPass123",
            "first_name": "Ana",
            "last_name": "García",
        },
    )


async def test_login_returns_access_and_sets_refresh_cookie(client: AsyncClient) -> None:
    await _register(client)
    response = await client.post(
        "/v1/auth/login",
        json={"email": "login@ejemplo.com", "password": "ValidPass123"},
    )
    assert response.status_code == 200
    body = response.json()
    assert "access_token" in body
    assert body["user"]["email"] == "login@ejemplo.com"
    assert "refresh_token" in response.cookies


async def test_login_invalid_password_returns_401(client: AsyncClient) -> None:
    await _register(client, email="badpass@ejemplo.com")
    response = await client.post(
        "/v1/auth/login",
        json={"email": "badpass@ejemplo.com", "password": "WrongPass999"},
    )
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "AUTH_INVALID_CREDENTIALS"


async def test_login_unknown_email_returns_401(client: AsyncClient) -> None:
    response = await client.post(
        "/v1/auth/login",
        json={"email": "unknown@ejemplo.com", "password": "ValidPass123"},
    )
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "AUTH_INVALID_CREDENTIALS"


async def test_login_locks_after_threshold(client: AsyncClient) -> None:
    await _register(client, email="lockme@ejemplo.com")
    for _ in range(10):
        r = await client.post(
            "/v1/auth/login",
            json={"email": "lockme@ejemplo.com", "password": "WrongPass999"},
        )
        assert r.status_code == 401
    # 11th attempt — even with the correct password — is locked.
    response = await client.post(
        "/v1/auth/login",
        json={"email": "lockme@ejemplo.com", "password": "ValidPass123"},
    )
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "AUTH_ACCOUNT_LOCKED"
