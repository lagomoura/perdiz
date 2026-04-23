"""Admin customization groups + options CRUD."""

from __future__ import annotations

from app.db.session import AsyncSessionLocal
from app.models.audit_log import AuditLog
from app.models.category import Category
from app.models.customization_option import CustomizationOption
from app.models.product import Product
from httpx import AsyncClient
from sqlalchemy import select

from tests.integration._helpers import (
    auth_header,
    register_and_promote_admin,
    register_user,
)


async def _make_admin_and_product(
    client: AsyncClient,
) -> tuple[dict[str, str], str]:
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
        await s.refresh(prod)
        return h, prod.id


# --- AuthZ ------------------------------------------------------------------


async def test_anonymous_blocked(client: AsyncClient) -> None:
    r = await client.get("/v1/admin/products/x/customization-groups")
    assert r.status_code == 401


async def test_non_admin_blocked_with_404(client: AsyncClient) -> None:
    token = await register_user(client)
    r = await client.get("/v1/admin/products/x/customization-groups", headers=auth_header(token))
    assert r.status_code == 404


# --- Groups -----------------------------------------------------------------


async def test_create_group_and_list(client: AsyncClient) -> None:
    h, pid = await _make_admin_and_product(client)
    r = await client.post(
        f"/v1/admin/products/{pid}/customization-groups",
        json={
            "name": "Color",
            "type": "COLOR",
            "required": True,
            "selection_mode": "single",
            "sort_order": 0,
            "metadata": {"swatch_size": 32},
        },
        headers=h,
    )
    assert r.status_code == 201, r.text
    g = r.json()["group"]
    assert g["name"] == "Color"
    assert g["metadata"]["swatch_size"] == 32

    listing = await client.get(f"/v1/admin/products/{pid}/customization-groups", headers=h)
    assert len(listing.json()["data"]) == 1


async def test_create_group_unknown_product_is_404(client: AsyncClient) -> None:
    h, _ = await _make_admin_and_product(client)
    r = await client.post(
        "/v1/admin/products/01HWFAKEFAKEFAKEFAKEFAKEFA/customization-groups",
        json={
            "name": "X",
            "type": "COLOR",
            "required": False,
            "selection_mode": "single",
            "sort_order": 0,
            "metadata": {},
        },
        headers=h,
    )
    assert r.status_code == 404


async def test_update_and_delete_group(client: AsyncClient) -> None:
    h, pid = await _make_admin_and_product(client)
    gid = (
        await client.post(
            f"/v1/admin/products/{pid}/customization-groups",
            json={
                "name": "Material",
                "type": "MATERIAL",
                "required": False,
                "selection_mode": "single",
                "sort_order": 1,
                "metadata": {},
            },
            headers=h,
        )
    ).json()["group"]["id"]

    r = await client.patch(
        f"/v1/admin/products/{pid}/customization-groups/{gid}",
        json={"required": True, "sort_order": 5},
        headers=h,
    )
    assert r.status_code == 200
    assert r.json()["group"]["required"] is True
    assert r.json()["group"]["sort_order"] == 5

    r = await client.delete(f"/v1/admin/products/{pid}/customization-groups/{gid}", headers=h)
    assert r.status_code == 204


# --- Options ----------------------------------------------------------------


async def test_create_option_with_default_clears_others_in_single(
    client: AsyncClient,
) -> None:
    h, pid = await _make_admin_and_product(client)
    gid = (
        await client.post(
            f"/v1/admin/products/{pid}/customization-groups",
            json={
                "name": "Color",
                "type": "COLOR",
                "required": True,
                "selection_mode": "single",
                "sort_order": 0,
                "metadata": {},
            },
            headers=h,
        )
    ).json()["group"]["id"]

    await client.post(
        f"/v1/admin/customization-groups/{gid}/options",
        json={
            "label": "Rojo",
            "price_modifier_cents": 0,
            "is_default": True,
            "is_available": True,
            "sort_order": 0,
            "metadata": {"hex": "#FF0000"},
        },
        headers=h,
    )
    r2 = await client.post(
        f"/v1/admin/customization-groups/{gid}/options",
        json={
            "label": "Azul",
            "price_modifier_cents": 0,
            "is_default": True,
            "is_available": True,
            "sort_order": 1,
            "metadata": {"hex": "#0000FF"},
        },
        headers=h,
    )
    assert r2.status_code == 201

    listing = await client.get(f"/v1/admin/customization-groups/{gid}/options", headers=h)
    options = listing.json()["data"]
    defaults = [o for o in options if o["is_default"]]
    assert len(defaults) == 1 and defaults[0]["label"] == "Azul"


async def test_update_option_to_default_clears_others(client: AsyncClient) -> None:
    h, pid = await _make_admin_and_product(client)
    gid = (
        await client.post(
            f"/v1/admin/products/{pid}/customization-groups",
            json={
                "name": "Color",
                "type": "COLOR",
                "required": False,
                "selection_mode": "single",
                "sort_order": 0,
                "metadata": {},
            },
            headers=h,
        )
    ).json()["group"]["id"]

    first = (
        await client.post(
            f"/v1/admin/customization-groups/{gid}/options",
            json={
                "label": "A",
                "price_modifier_cents": 0,
                "is_default": True,
                "is_available": True,
                "sort_order": 0,
                "metadata": {},
            },
            headers=h,
        )
    ).json()["option"]["id"]
    second = (
        await client.post(
            f"/v1/admin/customization-groups/{gid}/options",
            json={
                "label": "B",
                "price_modifier_cents": 0,
                "is_default": False,
                "is_available": True,
                "sort_order": 1,
                "metadata": {},
            },
            headers=h,
        )
    ).json()["option"]["id"]

    await client.patch(
        f"/v1/admin/customization-groups/{gid}/options/{second}",
        json={"is_default": True},
        headers=h,
    )

    async with AsyncSessionLocal() as s:
        rows = (
            (
                await s.execute(
                    select(CustomizationOption).where(CustomizationOption.group_id == gid)
                )
            )
            .scalars()
            .all()
        )
        defaults = [o.id for o in rows if o.is_default]
        assert defaults == [second]
        _ = first


async def test_multiple_selection_allows_multiple_defaults(
    client: AsyncClient,
) -> None:
    h, pid = await _make_admin_and_product(client)
    gid = (
        await client.post(
            f"/v1/admin/products/{pid}/customization-groups",
            json={
                "name": "Colores",
                "type": "COLOR",
                "required": False,
                "selection_mode": "multiple",
                "sort_order": 0,
                "metadata": {},
            },
            headers=h,
        )
    ).json()["group"]["id"]

    await client.post(
        f"/v1/admin/customization-groups/{gid}/options",
        json={
            "label": "A",
            "price_modifier_cents": 0,
            "is_default": True,
            "is_available": True,
            "sort_order": 0,
            "metadata": {},
        },
        headers=h,
    )
    await client.post(
        f"/v1/admin/customization-groups/{gid}/options",
        json={
            "label": "B",
            "price_modifier_cents": 0,
            "is_default": True,
            "is_available": True,
            "sort_order": 1,
            "metadata": {},
        },
        headers=h,
    )

    listing = await client.get(f"/v1/admin/customization-groups/{gid}/options", headers=h)
    defaults = [o for o in listing.json()["data"] if o["is_default"]]
    assert len(defaults) == 2


async def test_delete_option(client: AsyncClient) -> None:
    h, pid = await _make_admin_and_product(client)
    gid = (
        await client.post(
            f"/v1/admin/products/{pid}/customization-groups",
            json={
                "name": "X",
                "type": "COLOR",
                "required": False,
                "selection_mode": "single",
                "sort_order": 0,
                "metadata": {},
            },
            headers=h,
        )
    ).json()["group"]["id"]
    oid = (
        await client.post(
            f"/v1/admin/customization-groups/{gid}/options",
            json={
                "label": "X",
                "price_modifier_cents": 0,
                "is_default": False,
                "is_available": True,
                "sort_order": 0,
                "metadata": {},
            },
            headers=h,
        )
    ).json()["option"]["id"]

    r = await client.delete(f"/v1/admin/customization-groups/{gid}/options/{oid}", headers=h)
    assert r.status_code == 204


# --- Audit ------------------------------------------------------------------


async def test_group_and_option_are_audited(client: AsyncClient) -> None:
    h, pid = await _make_admin_and_product(client)
    gid = (
        await client.post(
            f"/v1/admin/products/{pid}/customization-groups",
            json={
                "name": "Color",
                "type": "COLOR",
                "required": False,
                "selection_mode": "single",
                "sort_order": 0,
                "metadata": {},
            },
            headers=h,
        )
    ).json()["group"]["id"]

    oid = (
        await client.post(
            f"/v1/admin/customization-groups/{gid}/options",
            json={
                "label": "A",
                "price_modifier_cents": 0,
                "is_default": False,
                "is_available": True,
                "sort_order": 0,
                "metadata": {},
            },
            headers=h,
        )
    ).json()["option"]["id"]

    async with AsyncSessionLocal() as s:
        rows = (
            (
                await s.execute(
                    select(AuditLog)
                    .where(AuditLog.entity_id.in_([gid, oid]))
                    .order_by(AuditLog.created_at.asc())
                )
            )
            .scalars()
            .all()
        )
        actions = sorted(r.action for r in rows)
        assert actions == [
            "customization_group.create",
            "customization_option.create",
        ]
