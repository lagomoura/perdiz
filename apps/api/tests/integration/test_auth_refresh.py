from __future__ import annotations

from httpx import AsyncClient


async def _login(client: AsyncClient, email: str = "refresh@ejemplo.com") -> str:
    await client.post(
        "/v1/auth/register",
        json={"email": email, "password": "ValidPass123", "first_name": None, "last_name": None},
    )
    r = await client.post(
        "/v1/auth/login", json={"email": email, "password": "ValidPass123"}
    )
    return r.cookies["refresh_token"]


async def test_refresh_rotates_token(client: AsyncClient) -> None:
    old_cookie = await _login(client)
    response = await client.post("/v1/auth/refresh")
    assert response.status_code == 200
    assert "access_token" in response.json()
    new_cookie = response.cookies["refresh_token"]
    assert new_cookie != old_cookie


async def test_refresh_without_cookie_returns_401(client: AsyncClient) -> None:
    # Make sure no cookie is sent
    client.cookies.clear()
    response = await client.post("/v1/auth/refresh")
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "AUTH_REFRESH_INVALID"


async def test_refresh_reuse_revokes_family(client: AsyncClient) -> None:
    old_cookie = await _login(client, email="reuse@ejemplo.com")
    # First refresh succeeds
    r1 = await client.post("/v1/auth/refresh")
    assert r1.status_code == 200
    rotated_cookie = r1.cookies["refresh_token"]
    # Replay the OLD cookie: reuse must be detected.
    client.cookies.clear()
    client.cookies.set("refresh_token", old_cookie, domain="test", path="/v1/auth")
    r2 = await client.post("/v1/auth/refresh")
    assert r2.status_code == 401
    assert r2.json()["error"]["code"] == "AUTH_REFRESH_REUSED"
    # The cookie issued by r1 is also invalid now (family revoked).
    client.cookies.clear()
    client.cookies.set("refresh_token", rotated_cookie, domain="test", path="/v1/auth")
    r3 = await client.post("/v1/auth/refresh")
    assert r3.status_code == 401


async def test_logout_clears_cookie(client: AsyncClient) -> None:
    await _login(client, email="logout@ejemplo.com")
    r = await client.post("/v1/auth/logout")
    assert r.status_code == 204
    # After logout, refresh should fail
    r2 = await client.post("/v1/auth/refresh")
    assert r2.status_code == 401
