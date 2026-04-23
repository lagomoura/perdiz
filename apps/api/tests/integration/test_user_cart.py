"""User cart flow: add/update/remove items, customization validation,
dedupe, apply/remove coupon, totals.
"""

from __future__ import annotations

from datetime import UTC, datetime

from app.db.session import AsyncSessionLocal
from app.models.category import Category
from app.models.coupon import Coupon
from app.models.customization_group import CustomizationGroup
from app.models.customization_option import CustomizationOption
from app.models.media_file import MediaFile
from app.models.product import Product
from app.models.user import User
from httpx import AsyncClient
from sqlalchemy import update

from tests.integration._helpers import auth_header, register_user


async def _verify(email: str) -> None:
    async with AsyncSessionLocal() as s:
        await s.execute(
            update(User).where(User.email == email).values(email_verified_at=datetime.now(tz=UTC))
        )
        await s.commit()


async def _verified(client: AsyncClient, *, email: str = "cart@example.com") -> str:
    token = await register_user(client, email=email)
    await _verify(email)
    return token


async def _seed_product(
    *,
    slug: str = "prod",
    sku: str | None = None,
    price: int = 100_00,
    stock: int | None = 10,
    stock_mode: str = "stocked",
) -> tuple[str, str]:
    async with AsyncSessionLocal() as s:
        cat = Category(name="C", slug=f"c-{slug}", sort_order=0)
        s.add(cat)
        await s.flush()
        p = Product(
            category_id=cat.id,
            name=f"Product {slug}",
            slug=slug,
            base_price_cents=price,
            stock_mode=stock_mode,
            stock_quantity=stock if stock_mode == "stocked" else None,
            lead_time_days=None if stock_mode == "stocked" else 3,
            sku=sku or f"SKU-{slug.upper()}",
            status="active",
        )
        s.add(p)
        await s.commit()
        await s.refresh(p)
        return p.id, cat.id


# --- AuthZ ---------------------------------------------------------------


async def test_anonymous_blocked(client: AsyncClient) -> None:
    r = await client.get("/v1/cart")
    assert r.status_code == 401


async def test_unverified_user_blocked(client: AsyncClient) -> None:
    token = await register_user(client, email="unverified-cart@example.com")
    r = await client.get("/v1/cart", headers=auth_header(token))
    assert r.status_code == 403


# --- Add / get ----------------------------------------------------------


async def test_get_auto_creates_empty_cart(client: AsyncClient) -> None:
    h = auth_header(await _verified(client))
    r = await client.get("/v1/cart", headers=h)
    assert r.status_code == 200
    body = r.json()["cart"]
    assert body["items"] == []
    assert body["total_cents"] == 0
    assert body["coupon"] is None


async def test_add_item_no_customization(client: AsyncClient) -> None:
    h = auth_header(await _verified(client))
    pid, _ = await _seed_product(slug="plain", price=50_00)
    r = await client.post(
        "/v1/cart/items",
        json={"product_id": pid, "quantity": 2, "selections": []},
        headers=h,
    )
    assert r.status_code == 201, r.text
    cart = r.json()["cart"]
    assert len(cart["items"]) == 1
    assert cart["items"][0]["quantity"] == 2
    assert cart["subtotal_cents"] == 100_00
    assert cart["total_cents"] == 100_00


async def test_dedupe_adds_quantity(client: AsyncClient) -> None:
    h = auth_header(await _verified(client))
    pid, _ = await _seed_product(slug="dedup", price=30_00)
    for _ in range(2):
        await client.post(
            "/v1/cart/items",
            json={"product_id": pid, "quantity": 2, "selections": []},
            headers=h,
        )
    body = (await client.get("/v1/cart", headers=h)).json()["cart"]
    assert len(body["items"]) == 1
    assert body["items"][0]["quantity"] == 4
    assert body["subtotal_cents"] == 120_00


async def test_add_item_rejects_missing_product(client: AsyncClient) -> None:
    h = auth_header(await _verified(client))
    r = await client.post(
        "/v1/cart/items",
        json={
            "product_id": "01HWFAKEFAKEFAKEFAKEFAKEFA",
            "quantity": 1,
            "selections": [],
        },
        headers=h,
    )
    assert r.status_code == 404


async def test_add_item_rejects_out_of_stock(client: AsyncClient) -> None:
    h = auth_header(await _verified(client))
    pid, _ = await _seed_product(slug="nostk", stock=1)
    r = await client.post(
        "/v1/cart/items",
        json={"product_id": pid, "quantity": 5, "selections": []},
        headers=h,
    )
    assert r.status_code == 409
    assert r.json()["error"]["code"] == "BUSINESS_RULE_VIOLATION"


# --- Customization validation -------------------------------------------


async def _seed_with_color_group(
    product_id: str,
) -> tuple[str, str, str]:
    """Return (group_id, option_rojo_id, option_azul_id)."""
    async with AsyncSessionLocal() as s:
        group = CustomizationGroup(
            product_id=product_id,
            name="Color",
            type="COLOR",
            required=True,
            selection_mode="single",
            sort_order=0,
        )
        s.add(group)
        await s.flush()
        rojo = CustomizationOption(
            group_id=group.id,
            label="Rojo",
            price_modifier_cents=500,
        )
        azul = CustomizationOption(
            group_id=group.id,
            label="Azul",
            price_modifier_cents=0,
        )
        s.add(rojo)
        s.add(azul)
        await s.commit()
        return group.id, rojo.id, azul.id


async def test_required_group_missing_rejected(client: AsyncClient) -> None:
    h = auth_header(await _verified(client))
    pid, _ = await _seed_product(slug="customreq")
    await _seed_with_color_group(pid)
    r = await client.post(
        "/v1/cart/items",
        json={"product_id": pid, "quantity": 1, "selections": []},
        headers=h,
    )
    assert r.status_code == 422
    assert r.json()["error"]["details"]["code"] == "CUSTOMIZATION_REQUIRED_GROUP_MISSING"


async def test_color_selection_computes_modifier(client: AsyncClient) -> None:
    h = auth_header(await _verified(client))
    pid, _ = await _seed_product(slug="colorsel", price=100_00)
    gid, rojo_id, azul_id = await _seed_with_color_group(pid)

    r = await client.post(
        "/v1/cart/items",
        json={
            "product_id": pid,
            "quantity": 1,
            "selections": [{"group_id": gid, "option_ids": [rojo_id]}],
        },
        headers=h,
    )
    assert r.status_code == 201, r.text
    cart = r.json()["cart"]
    item = cart["items"][0]
    assert item["modifiers_total_cents"] == 500
    assert item["line_total_cents"] == 100_00 + 500
    assert cart["subtotal_cents"] == 100_00 + 500
    _ = azul_id


async def test_invalid_option_id_rejected(client: AsyncClient) -> None:
    h = auth_header(await _verified(client))
    pid, _ = await _seed_product(slug="invopt")
    gid, _rojo, _azul = await _seed_with_color_group(pid)
    r = await client.post(
        "/v1/cart/items",
        json={
            "product_id": pid,
            "quantity": 1,
            "selections": [{"group_id": gid, "option_ids": ["01HWFAKEOPTIONOPTIONOPTION"]}],
        },
        headers=h,
    )
    assert r.status_code == 422
    assert r.json()["error"]["details"]["code"] == "CUSTOMIZATION_INVALID_OPTION"


async def test_dedupe_with_same_customization(client: AsyncClient) -> None:
    h = auth_header(await _verified(client))
    pid, _ = await _seed_product(slug="dupecust")
    gid, rojo_id, _ = await _seed_with_color_group(pid)
    for _ in range(2):
        await client.post(
            "/v1/cart/items",
            json={
                "product_id": pid,
                "quantity": 1,
                "selections": [{"group_id": gid, "option_ids": [rojo_id]}],
            },
            headers=h,
        )
    cart = (await client.get("/v1/cart", headers=h)).json()["cart"]
    assert len(cart["items"]) == 1
    assert cart["items"][0]["quantity"] == 2


async def test_different_customization_creates_new_line(
    client: AsyncClient,
) -> None:
    h = auth_header(await _verified(client))
    pid, _ = await _seed_product(slug="difcust")
    gid, rojo_id, azul_id = await _seed_with_color_group(pid)
    await client.post(
        "/v1/cart/items",
        json={
            "product_id": pid,
            "quantity": 1,
            "selections": [{"group_id": gid, "option_ids": [rojo_id]}],
        },
        headers=h,
    )
    await client.post(
        "/v1/cart/items",
        json={
            "product_id": pid,
            "quantity": 2,
            "selections": [{"group_id": gid, "option_ids": [azul_id]}],
        },
        headers=h,
    )
    cart = (await client.get("/v1/cart", headers=h)).json()["cart"]
    assert len(cart["items"]) == 2


# --- Engraving text + file types -------------------------------------------


async def _seed_text_group(product_id: str, *, modifier: int = 200) -> str:
    async with AsyncSessionLocal() as s:
        group = CustomizationGroup(
            product_id=product_id,
            name="Grabado",
            type="ENGRAVING_TEXT",
            required=False,
            selection_mode="single",
            sort_order=0,
            group_metadata={
                "min_length": 1,
                "max_length": 10,
                "allowed_charset": "alphanumeric_spaces",
            },
        )
        s.add(group)
        await s.flush()
        virtual = CustomizationOption(
            group_id=group.id,
            label="user_input",
            price_modifier_cents=modifier,
        )
        s.add(virtual)
        await s.commit()
        return group.id


async def test_engraving_text_validates_length(client: AsyncClient) -> None:
    h = auth_header(await _verified(client))
    pid, _ = await _seed_product(slug="engtext")
    gid = await _seed_text_group(pid)
    # Too long (max 10).
    r = await client.post(
        "/v1/cart/items",
        json={
            "product_id": pid,
            "quantity": 1,
            "selections": [{"group_id": gid, "value": "un texto demasiado largo"}],
        },
        headers=h,
    )
    assert r.status_code == 422


async def test_engraving_text_charset_enforced(client: AsyncClient) -> None:
    h = auth_header(await _verified(client))
    pid, _ = await _seed_product(slug="engchar")
    gid = await _seed_text_group(pid)
    r = await client.post(
        "/v1/cart/items",
        json={
            "product_id": pid,
            "quantity": 1,
            "selections": [{"group_id": gid, "value": "hola!#@"}],
        },
        headers=h,
    )
    assert r.status_code == 422


async def test_engraving_text_ok(client: AsyncClient) -> None:
    h = auth_header(await _verified(client))
    pid, _ = await _seed_product(slug="engok", price=200_00)
    gid = await _seed_text_group(pid, modifier=300)
    r = await client.post(
        "/v1/cart/items",
        json={
            "product_id": pid,
            "quantity": 1,
            "selections": [{"group_id": gid, "value": "Juan"}],
        },
        headers=h,
    )
    assert r.status_code == 201, r.text
    item = r.json()["cart"]["items"][0]
    assert item["modifiers_total_cents"] == 300


async def test_user_file_must_belong_to_actor(client: AsyncClient) -> None:
    h = auth_header(await _verified(client))
    pid, _ = await _seed_product(slug="uf")
    # Group that expects user_upload_image.
    async with AsyncSessionLocal() as s:
        group = CustomizationGroup(
            product_id=pid,
            name="Grabado img",
            type="ENGRAVING_IMAGE",
            required=False,
            selection_mode="single",
            sort_order=0,
            group_metadata={},
        )
        s.add(group)
        await s.flush()
        s.add(CustomizationOption(group_id=group.id, label="user_input", price_modifier_cents=0))
        # A file owned by a DIFFERENT user.
        other = User(email="other@example.com", role="user")
        s.add(other)
        await s.flush()
        alien = MediaFile(
            owner_user_id=other.id,
            kind="user_upload_image",
            mime_type="image/png",
            size_bytes=10,
            storage_key="uploads/images/alien/x.png",
        )
        s.add(alien)
        await s.commit()
        gid = group.id
        alien_id = alien.id

    r = await client.post(
        "/v1/cart/items",
        json={
            "product_id": pid,
            "quantity": 1,
            "selections": [{"group_id": gid, "file_id": alien_id}],
        },
        headers=h,
    )
    assert r.status_code == 422
    assert r.json()["error"]["details"]["code"] == "CUSTOMIZATION_INVALID_OPTION"


# --- Update / remove -------------------------------------------------------


async def test_update_quantity(client: AsyncClient) -> None:
    h = auth_header(await _verified(client))
    pid, _ = await _seed_product(slug="upd")
    create = await client.post(
        "/v1/cart/items",
        json={"product_id": pid, "quantity": 1, "selections": []},
        headers=h,
    )
    item_id = create.json()["cart"]["items"][0]["id"]
    r = await client.patch(f"/v1/cart/items/{item_id}", json={"quantity": 5}, headers=h)
    assert r.status_code == 200
    assert r.json()["cart"]["items"][0]["quantity"] == 5


async def test_remove_item(client: AsyncClient) -> None:
    h = auth_header(await _verified(client))
    pid, _ = await _seed_product(slug="rmv")
    create = await client.post(
        "/v1/cart/items",
        json={"product_id": pid, "quantity": 1, "selections": []},
        headers=h,
    )
    item_id = create.json()["cart"]["items"][0]["id"]
    r = await client.delete(f"/v1/cart/items/{item_id}", headers=h)
    assert r.status_code == 204
    listing = (await client.get("/v1/cart", headers=h)).json()["cart"]
    assert listing["items"] == []


# --- Coupon flow ---------------------------------------------------------


async def _seed_coupon(
    code: str = "VERANO20",
    *,
    type_: str = "percentage",
    value: int = 20,
    min_order: int = 0,
    status: str = "active",
) -> str:
    async with AsyncSessionLocal() as s:
        c = Coupon(
            code=code.lower(),
            type=type_,
            value=value,
            min_order_cents=min_order,
            status=status,
        )
        s.add(c)
        await s.commit()
        await s.refresh(c)
        return c.id


async def test_apply_coupon_percentage(client: AsyncClient) -> None:
    h = auth_header(await _verified(client))
    pid, _ = await _seed_product(slug="cupon", price=100_00)
    await _seed_coupon("VERANO20", value=20)
    await client.post(
        "/v1/cart/items",
        json={"product_id": pid, "quantity": 2, "selections": []},
        headers=h,
    )
    r = await client.post("/v1/cart/coupon", json={"code": "VERANO20"}, headers=h)
    assert r.status_code == 200, r.text
    cart = r.json()["cart"]
    assert cart["coupon"]["code"] == "verano20"
    assert cart["subtotal_cents"] == 200_00
    assert cart["coupon_discount_cents"] == 40_00
    assert cart["total_cents"] == 160_00


async def test_apply_coupon_case_insensitive(client: AsyncClient) -> None:
    h = auth_header(await _verified(client))
    pid, _ = await _seed_product(slug="cupci", price=50_00)
    await _seed_coupon("HELLO10", value=10)
    await client.post(
        "/v1/cart/items",
        json={"product_id": pid, "quantity": 1, "selections": []},
        headers=h,
    )
    r = await client.post("/v1/cart/coupon", json={"code": "hELLo10"}, headers=h)
    assert r.status_code == 200
    assert r.json()["cart"]["coupon"]["code"] == "hello10"


async def test_apply_coupon_unknown(client: AsyncClient) -> None:
    h = auth_header(await _verified(client))
    r = await client.post("/v1/cart/coupon", json={"code": "NOEXISTE"}, headers=h)
    assert r.status_code == 422
    assert r.json()["error"]["details"]["code"] == "COUPON_NOT_FOUND"


async def test_apply_coupon_min_order_not_met(client: AsyncClient) -> None:
    h = auth_header(await _verified(client))
    pid, _ = await _seed_product(slug="minor", price=20_00)
    await _seed_coupon("BIG", value=50, min_order=100_00)
    await client.post(
        "/v1/cart/items",
        json={"product_id": pid, "quantity": 1, "selections": []},
        headers=h,
    )
    r = await client.post("/v1/cart/coupon", json={"code": "BIG"}, headers=h)
    assert r.status_code == 422
    assert r.json()["error"]["details"]["code"] == "COUPON_MIN_ORDER_NOT_MET"


async def test_remove_coupon(client: AsyncClient) -> None:
    h = auth_header(await _verified(client))
    pid, _ = await _seed_product(slug="rmcup", price=100_00)
    await _seed_coupon("X10", value=10)
    await client.post(
        "/v1/cart/items",
        json={"product_id": pid, "quantity": 1, "selections": []},
        headers=h,
    )
    await client.post("/v1/cart/coupon", json={"code": "X10"}, headers=h)
    r = await client.delete("/v1/cart/coupon", headers=h)
    assert r.status_code == 200
    assert r.json()["cart"]["coupon"] is None
    assert r.json()["cart"]["coupon_discount_cents"] == 0
