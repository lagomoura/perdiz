"""Admin category CRUD."""

from __future__ import annotations

from app.db.session import AsyncSessionLocal
from app.models.audit_log import AuditLog
from app.models.category import Category
from httpx import AsyncClient
from sqlalchemy import select

from tests.integration._helpers import (
    auth_header,
    register_and_promote_admin,
    register_user,
)

# --- AuthZ ----------------------------------------------------------------


async def test_anonymous_cannot_list_returns_401(client: AsyncClient) -> None:
    r = await client.get("/v1/admin/categories")
    assert r.status_code == 401


async def test_non_admin_sees_404_on_list(client: AsyncClient) -> None:
    token = await register_user(client)
    r = await client.get("/v1/admin/categories", headers=auth_header(token))
    assert r.status_code == 404
    assert r.json()["error"]["code"] == "NOT_FOUND"


# --- CRUD ------------------------------------------------------------------


async def test_create_list_and_get(client: AsyncClient) -> None:
    admin_token = await register_and_promote_admin(client)
    h = auth_header(admin_token)

    r = await client.post(
        "/v1/admin/categories",
        json={
            "name": "Decoración",
            "slug": "decoracion",
            "parent_id": None,
            "description": None,
            "image_url": None,
            "sort_order": 1,
            "status": "active",
        },
        headers=h,
    )
    assert r.status_code == 201, r.text
    created = r.json()["category"]
    assert created["slug"] == "decoracion"
    assert created["status"] == "active"
    cid = created["id"]

    listing = await client.get("/v1/admin/categories", headers=h)
    assert len(listing.json()["data"]) == 1

    detail = await client.get(f"/v1/admin/categories/{cid}", headers=h)
    assert detail.status_code == 200
    assert detail.json()["category"]["slug"] == "decoracion"


async def test_create_rejects_duplicate_slug(client: AsyncClient) -> None:
    h = auth_header(await register_and_promote_admin(client))
    payload = {
        "name": "Una",
        "slug": "misma",
        "parent_id": None,
        "description": None,
        "image_url": None,
        "sort_order": 0,
        "status": "active",
    }
    r1 = await client.post("/v1/admin/categories", json=payload, headers=h)
    assert r1.status_code == 201
    payload["name"] = "Otra"
    r2 = await client.post("/v1/admin/categories", json=payload, headers=h)
    assert r2.status_code == 409
    assert r2.json()["error"]["code"] == "RESOURCE_CONFLICT"


async def test_create_rejects_invalid_slug_pattern(client: AsyncClient) -> None:
    h = auth_header(await register_and_promote_admin(client))
    r = await client.post(
        "/v1/admin/categories",
        json={
            "name": "X",
            "slug": "Invalid Slug!",
            "parent_id": None,
            "description": None,
            "image_url": None,
            "sort_order": 0,
            "status": "active",
        },
        headers=h,
    )
    assert r.status_code == 422


async def test_create_rejects_unknown_parent(client: AsyncClient) -> None:
    h = auth_header(await register_and_promote_admin(client))
    r = await client.post(
        "/v1/admin/categories",
        json={
            "name": "X",
            "slug": "x",
            "parent_id": "01HWFAKEFAKEFAKEFAKEFAKEFA",
            "description": None,
            "image_url": None,
            "sort_order": 0,
            "status": "active",
        },
        headers=h,
    )
    assert r.status_code == 422
    assert r.json()["error"]["code"] == "VALIDATION_ERROR"


async def test_update_patches_partial(client: AsyncClient) -> None:
    h = auth_header(await register_and_promote_admin(client))
    created = (
        await client.post(
            "/v1/admin/categories",
            json={
                "name": "Vieja",
                "slug": "vieja",
                "parent_id": None,
                "description": None,
                "image_url": None,
                "sort_order": 0,
                "status": "active",
            },
            headers=h,
        )
    ).json()["category"]

    r = await client.patch(
        f"/v1/admin/categories/{created['id']}",
        json={"name": "Nueva"},
        headers=h,
    )
    assert r.status_code == 200
    body = r.json()["category"]
    assert body["name"] == "Nueva"
    assert body["slug"] == "vieja"  # unchanged


async def test_update_rejects_self_as_parent(client: AsyncClient) -> None:
    h = auth_header(await register_and_promote_admin(client))
    created = (
        await client.post(
            "/v1/admin/categories",
            json={
                "name": "X",
                "slug": "x",
                "parent_id": None,
                "description": None,
                "image_url": None,
                "sort_order": 0,
                "status": "active",
            },
            headers=h,
        )
    ).json()["category"]

    r = await client.patch(
        f"/v1/admin/categories/{created['id']}",
        json={"parent_id": created["id"]},
        headers=h,
    )
    assert r.status_code == 422


async def test_delete_is_soft(client: AsyncClient) -> None:
    h = auth_header(await register_and_promote_admin(client))
    created = (
        await client.post(
            "/v1/admin/categories",
            json={
                "name": "Borrar",
                "slug": "borrar",
                "parent_id": None,
                "description": None,
                "image_url": None,
                "sort_order": 0,
                "status": "active",
            },
            headers=h,
        )
    ).json()["category"]

    r = await client.delete(f"/v1/admin/categories/{created['id']}", headers=h)
    assert r.status_code == 204

    # Not visible via list (deleted_at is not null).
    listing = await client.get("/v1/admin/categories", headers=h)
    assert all(c["id"] != created["id"] for c in listing.json()["data"])

    # Row still exists in DB with deleted_at set and status=archived.
    async with AsyncSessionLocal() as s:
        row = (await s.execute(select(Category).where(Category.id == created["id"]))).scalar_one()
        assert row.deleted_at is not None
        assert row.status == "archived"


# --- Audit log ------------------------------------------------------------


async def test_mutations_are_audited(client: AsyncClient) -> None:
    h = auth_header(await register_and_promote_admin(client))
    created = (
        await client.post(
            "/v1/admin/categories",
            json={
                "name": "Cat",
                "slug": "cat",
                "parent_id": None,
                "description": None,
                "image_url": None,
                "sort_order": 0,
                "status": "active",
            },
            headers=h,
        )
    ).json()["category"]

    await client.patch(f"/v1/admin/categories/{created['id']}", json={"name": "Cat 2"}, headers=h)
    await client.delete(f"/v1/admin/categories/{created['id']}", headers=h)

    async with AsyncSessionLocal() as s:
        rows = (
            (
                await s.execute(
                    select(AuditLog)
                    .where(AuditLog.entity_id == created["id"])
                    .order_by(AuditLog.created_at.asc())
                )
            )
            .scalars()
            .all()
        )
        actions = [r.action for r in rows]
        assert actions == ["category.create", "category.update", "category.delete"]
        for row in rows:
            assert row.actor_role == "admin"
            assert row.actor_id is not None
        # Update audit carries both before and after.
        update_row = rows[1]
        assert update_row.before_json is not None and update_row.after_json is not None
        assert update_row.before_json["name"] == "Cat"
        assert update_row.after_json["name"] == "Cat 2"
