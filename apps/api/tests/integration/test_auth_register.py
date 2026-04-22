from __future__ import annotations

from httpx import AsyncClient


async def test_register_creates_unverified_user(client: AsyncClient) -> None:
    response = await client.post(
        "/v1/auth/register",
        json={
            "email": "nuevo@ejemplo.com",
            "password": "ValidPass123",
            "first_name": "Juan",
            "last_name": "Pérez",
        },
    )
    assert response.status_code == 201
    body = response.json()
    assert body["user"]["email"] == "nuevo@ejemplo.com"
    assert body["user"]["email_verified"] is False
    assert body["user"]["role"] == "user"
    assert "id" in body["user"]


async def test_register_rejects_duplicate_email(client: AsyncClient) -> None:
    payload = {
        "email": "dup@ejemplo.com",
        "password": "ValidPass123",
        "first_name": "Juan",
        "last_name": "Pérez",
    }
    r1 = await client.post("/v1/auth/register", json=payload)
    assert r1.status_code == 201
    r2 = await client.post("/v1/auth/register", json=payload)
    assert r2.status_code == 409
    assert r2.json()["error"]["code"] == "RESOURCE_CONFLICT"


async def test_register_rejects_weak_password(client: AsyncClient) -> None:
    response = await client.post(
        "/v1/auth/register",
        json={
            "email": "weak@ejemplo.com",
            "password": "short",
            "first_name": None,
            "last_name": None,
        },
    )
    # pydantic rejects short password at min_length=10 → 422
    assert response.status_code == 422


async def test_register_rejects_password_without_digit(client: AsyncClient) -> None:
    response = await client.post(
        "/v1/auth/register",
        json={
            "email": "nodigit@ejemplo.com",
            "password": "onlylettersss",
            "first_name": None,
            "last_name": None,
        },
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"
