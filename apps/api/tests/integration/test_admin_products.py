"""Admin product CRUD and status transitions."""

from __future__ import annotations

from app.db.session import AsyncSessionLocal
from app.models.audit_log import AuditLog
from app.models.category import Category
from app.models.product import Product
from httpx import AsyncClient
from sqlalchemy import select

from tests.integration._helpers import (
    auth_header,
    register_and_promote_admin,
    register_user,
)


async def _make_admin_and_category(
    client: AsyncClient,
) -> tuple[dict[str, str], str]:
    h = auth_header(await register_and_promote_admin(client))
    async with AsyncSessionLocal() as s:
        cat = Category(name="Decoración", slug="decoracion", sort_order=0)
        s.add(cat)
        await s.commit()
        await s.refresh(cat)
        return h, cat.id


def _product_payload(
    category_id: str,
    *,
    slug: str = "prod-x",
    sku: str = "SKU-PRODX",
    stock_mode: str = "stocked",
    stock_quantity: int | None = 5,
    lead_time_days: int | None = None,
) -> dict:
    return {
        "category_id": category_id,
        "name": "Prod X",
        "slug": slug,
        "description": None,
        "base_price_cents": 100000,
        "stock_mode": stock_mode,
        "stock_quantity": stock_quantity,
        "lead_time_days": lead_time_days,
        "weight_grams": None,
        "dimensions_mm": None,
        "sku": sku,
        "tags": [],
        "status": "draft",
        "model_file_id": None,
    }


# --- AuthZ ---------------------------------------------------------------


async def test_anonymous_blocked(client: AsyncClient) -> None:
    r = await client.get("/v1/admin/products")
    assert r.status_code == 401


async def test_non_admin_blocked_with_404(client: AsyncClient) -> None:
    token = await register_user(client)
    r = await client.get("/v1/admin/products", headers=auth_header(token))
    assert r.status_code == 404


# --- Create --------------------------------------------------------------


async def test_create_product_in_draft_by_default(client: AsyncClient) -> None:
    h, cat_id = await _make_admin_and_category(client)
    r = await client.post("/v1/admin/products", json=_product_payload(cat_id), headers=h)
    assert r.status_code == 201, r.text
    body = r.json()["product"]
    assert body["status"] == "draft"
    assert body["category_id"] == cat_id


async def test_create_rejects_duplicate_slug(client: AsyncClient) -> None:
    h, cat_id = await _make_admin_and_category(client)
    await client.post("/v1/admin/products", json=_product_payload(cat_id, slug="dup"), headers=h)
    r = await client.post(
        "/v1/admin/products",
        json=_product_payload(cat_id, slug="dup", sku="SKU-OTHER"),
        headers=h,
    )
    assert r.status_code == 409
    assert r.json()["error"]["code"] == "RESOURCE_CONFLICT"


async def test_create_rejects_unknown_category(client: AsyncClient) -> None:
    h = auth_header(await register_and_promote_admin(client))
    r = await client.post(
        "/v1/admin/products",
        json=_product_payload("01HWFAKEFAKEFAKEFAKEFAKEFA"),
        headers=h,
    )
    assert r.status_code == 422


async def test_create_rejects_inconsistent_stock_mode(client: AsyncClient) -> None:
    h, cat_id = await _make_admin_and_category(client)
    r = await client.post(
        "/v1/admin/products",
        json=_product_payload(
            cat_id, stock_mode="print_on_demand", stock_quantity=1, lead_time_days=None
        ),
        headers=h,
    )
    assert r.status_code == 422


async def test_create_pod_with_lead_time_ok(client: AsyncClient) -> None:
    h, cat_id = await _make_admin_and_category(client)
    r = await client.post(
        "/v1/admin/products",
        json=_product_payload(
            cat_id, stock_mode="print_on_demand", stock_quantity=None, lead_time_days=5
        ),
        headers=h,
    )
    assert r.status_code == 201


# --- Update --------------------------------------------------------------


async def test_update_partial_fields(client: AsyncClient) -> None:
    h, cat_id = await _make_admin_and_category(client)
    created = (
        await client.post("/v1/admin/products", json=_product_payload(cat_id), headers=h)
    ).json()["product"]

    r = await client.patch(
        f"/v1/admin/products/{created['id']}",
        json={"name": "Renombrado", "base_price_cents": 120000},
        headers=h,
    )
    assert r.status_code == 200
    body = r.json()["product"]
    assert body["name"] == "Renombrado"
    assert body["base_price_cents"] == 120000
    assert body["slug"] == "prod-x"  # unchanged


# --- Status transitions --------------------------------------------------


async def test_transition_draft_to_active_and_archive(client: AsyncClient) -> None:
    h, cat_id = await _make_admin_and_category(client)
    pid = (
        await client.post("/v1/admin/products", json=_product_payload(cat_id), headers=h)
    ).json()["product"]["id"]

    r = await client.post(
        f"/v1/admin/products/{pid}/transition-status",
        json={"status": "active"},
        headers=h,
    )
    assert r.status_code == 200
    assert r.json()["product"]["status"] == "active"

    r = await client.post(
        f"/v1/admin/products/{pid}/transition-status",
        json={"status": "archived"},
        headers=h,
    )
    assert r.json()["product"]["status"] == "archived"


async def test_transition_noop_same_status(client: AsyncClient) -> None:
    h, cat_id = await _make_admin_and_category(client)
    pid = (
        await client.post("/v1/admin/products", json=_product_payload(cat_id), headers=h)
    ).json()["product"]["id"]
    r = await client.post(
        f"/v1/admin/products/{pid}/transition-status",
        json={"status": "draft"},
        headers=h,
    )
    assert r.status_code == 200


# --- Delete --------------------------------------------------------------


async def test_delete_is_soft(client: AsyncClient) -> None:
    h, cat_id = await _make_admin_and_category(client)
    pid = (
        await client.post("/v1/admin/products", json=_product_payload(cat_id), headers=h)
    ).json()["product"]["id"]

    r = await client.delete(f"/v1/admin/products/{pid}", headers=h)
    assert r.status_code == 204

    async with AsyncSessionLocal() as s:
        row = (await s.execute(select(Product).where(Product.id == pid))).scalar_one()
        assert row.deleted_at is not None
        assert row.status == "archived"


# --- Audit ---------------------------------------------------------------


async def test_product_mutations_are_audited(client: AsyncClient) -> None:
    h, cat_id = await _make_admin_and_category(client)
    pid = (
        await client.post("/v1/admin/products", json=_product_payload(cat_id), headers=h)
    ).json()["product"]["id"]

    await client.patch(f"/v1/admin/products/{pid}", json={"name": "X"}, headers=h)
    await client.post(
        f"/v1/admin/products/{pid}/transition-status",
        json={"status": "active"},
        headers=h,
    )
    await client.delete(f"/v1/admin/products/{pid}", headers=h)

    async with AsyncSessionLocal() as s:
        rows = (
            (
                await s.execute(
                    select(AuditLog)
                    .where(AuditLog.entity_id == pid)
                    .order_by(AuditLog.created_at.asc())
                )
            )
            .scalars()
            .all()
        )
        assert [r.action for r in rows] == [
            "product.create",
            "product.update",
            "product.status.transition",
            "product.delete",
        ]
