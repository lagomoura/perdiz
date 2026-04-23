"""Admin discounts CRUD: volume (per product) and automatic (global)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from app.db.session import AsyncSessionLocal
from app.models.audit_log import AuditLog
from app.models.category import Category
from app.models.product import Product
from httpx import AsyncClient
from sqlalchemy import select

from tests.integration._helpers import auth_header, register_and_promote_admin


async def _setup(client: AsyncClient) -> tuple[dict[str, str], str, str]:
    h = auth_header(await register_and_promote_admin(client))
    async with AsyncSessionLocal() as s:
        cat = Category(name="C", slug="c", sort_order=0)
        s.add(cat)
        await s.flush()
        prod = Product(
            category_id=cat.id,
            name="P",
            slug="p",
            base_price_cents=1000,
            stock_mode="stocked",
            stock_quantity=1,
            sku="SKU-P",
            status="active",
        )
        s.add(prod)
        await s.commit()
        await s.refresh(cat)
        await s.refresh(prod)
        return h, cat.id, prod.id


# --- Volume discounts -------------------------------------------------------


async def test_create_and_list_volume_discount(client: AsyncClient) -> None:
    h, _, pid = await _setup(client)
    r = await client.post(
        f"/v1/admin/products/{pid}/volume-discounts",
        json={"min_quantity": 3, "type": "percentage", "value": 10},
        headers=h,
    )
    assert r.status_code == 201
    d = r.json()["discount"]
    assert d["product_id"] == pid

    listing = await client.get(f"/v1/admin/products/{pid}/volume-discounts", headers=h)
    assert len(listing.json()["data"]) == 1


async def test_volume_min_quantity_below_threshold_422(client: AsyncClient) -> None:
    h, _, pid = await _setup(client)
    r = await client.post(
        f"/v1/admin/products/{pid}/volume-discounts",
        json={"min_quantity": 1, "type": "percentage", "value": 10},
        headers=h,
    )
    assert r.status_code == 422


async def test_volume_percentage_out_of_range(client: AsyncClient) -> None:
    h, _, pid = await _setup(client)
    r = await client.post(
        f"/v1/admin/products/{pid}/volume-discounts",
        json={"min_quantity": 2, "type": "percentage", "value": 150},
        headers=h,
    )
    assert r.status_code == 422


async def test_delete_volume_discount(client: AsyncClient) -> None:
    h, _, pid = await _setup(client)
    did = (
        await client.post(
            f"/v1/admin/products/{pid}/volume-discounts",
            json={"min_quantity": 2, "type": "fixed", "value": 500},
            headers=h,
        )
    ).json()["discount"]["id"]
    r = await client.delete(f"/v1/admin/products/{pid}/volume-discounts/{did}", headers=h)
    assert r.status_code == 204


# --- Automatic discounts ----------------------------------------------------


async def test_automatic_scope_category_validates_target(
    client: AsyncClient,
) -> None:
    h, cat_id, _ = await _setup(client)
    r = await client.post(
        "/v1/admin/discounts",
        json={
            "name": "Cat 10%",
            "type": "percentage",
            "value": 10,
            "scope": "category",
            "target_id": cat_id,
            "valid_from": None,
            "valid_until": None,
            "status": "active",
        },
        headers=h,
    )
    assert r.status_code == 201


async def test_automatic_scope_category_unknown_target_422(
    client: AsyncClient,
) -> None:
    h, _, _ = await _setup(client)
    r = await client.post(
        "/v1/admin/discounts",
        json={
            "name": "Cat 10%",
            "type": "percentage",
            "value": 10,
            "scope": "category",
            "target_id": "01HWFAKEFAKEFAKEFAKEFAKEFA",
            "valid_from": None,
            "valid_until": None,
            "status": "active",
        },
        headers=h,
    )
    assert r.status_code == 422


async def test_automatic_valid_window_must_be_ordered(
    client: AsyncClient,
) -> None:
    h, cat_id, _ = await _setup(client)
    now = datetime.now(tz=UTC)
    r = await client.post(
        "/v1/admin/discounts",
        json={
            "name": "Inválido",
            "type": "percentage",
            "value": 10,
            "scope": "category",
            "target_id": cat_id,
            "valid_from": (now + timedelta(days=5)).isoformat(),
            "valid_until": now.isoformat(),
            "status": "active",
        },
        headers=h,
    )
    assert r.status_code == 422


async def test_update_and_delete_automatic(client: AsyncClient) -> None:
    h, cat_id, pid = await _setup(client)
    did = (
        await client.post(
            "/v1/admin/discounts",
            json={
                "name": "A",
                "type": "percentage",
                "value": 10,
                "scope": "category",
                "target_id": cat_id,
                "valid_from": None,
                "valid_until": None,
                "status": "active",
            },
            headers=h,
        )
    ).json()["discount"]["id"]

    r = await client.patch(
        f"/v1/admin/discounts/{did}",
        json={"value": 20, "scope": "product", "target_id": pid},
        headers=h,
    )
    assert r.status_code == 200
    body = r.json()["discount"]
    assert body["value"] == 20
    assert body["scope"] == "product"

    r = await client.delete(f"/v1/admin/discounts/{did}", headers=h)
    assert r.status_code == 204


async def test_list_filters_automatic(client: AsyncClient) -> None:
    h, cat_id, pid = await _setup(client)
    await client.post(
        "/v1/admin/discounts",
        json={
            "name": "A cat",
            "type": "percentage",
            "value": 10,
            "scope": "category",
            "target_id": cat_id,
            "valid_from": None,
            "valid_until": None,
            "status": "active",
        },
        headers=h,
    )
    await client.post(
        "/v1/admin/discounts",
        json={
            "name": "A prod disabled",
            "type": "fixed",
            "value": 500,
            "scope": "product",
            "target_id": pid,
            "valid_from": None,
            "valid_until": None,
            "status": "disabled",
        },
        headers=h,
    )

    r = await client.get("/v1/admin/discounts?status=active", headers=h)
    assert len(r.json()["data"]) == 1
    r = await client.get("/v1/admin/discounts?scope=product", headers=h)
    assert len(r.json()["data"]) == 1


# --- Audit ------------------------------------------------------------------


async def test_discount_mutations_audited(client: AsyncClient) -> None:
    h, _, pid = await _setup(client)
    did = (
        await client.post(
            f"/v1/admin/products/{pid}/volume-discounts",
            json={"min_quantity": 2, "type": "percentage", "value": 5},
            headers=h,
        )
    ).json()["discount"]["id"]
    await client.delete(f"/v1/admin/products/{pid}/volume-discounts/{did}", headers=h)

    async with AsyncSessionLocal() as s:
        rows = (
            (
                await s.execute(
                    select(AuditLog)
                    .where(AuditLog.entity_id == did)
                    .order_by(AuditLog.created_at.asc())
                )
            )
            .scalars()
            .all()
        )
        assert [r.action for r in rows] == [
            "volume_discount.create",
            "volume_discount.delete",
        ]
