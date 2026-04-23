"""User order history: list, detail, ownership, pagination."""

from __future__ import annotations

from httpx import AsyncClient

from tests.integration._helpers import auth_header, register_user
from tests.integration._order_helpers import (
    SHIPPING,
    checkout_as,
    register_verified,
    seed_product,
)


async def test_anonymous_blocked(client: AsyncClient) -> None:
    r = await client.get("/v1/orders")
    assert r.status_code == 401


async def test_unverified_user_blocked(client: AsyncClient) -> None:
    token = await register_user(client, email="unverified-orders@example.com")
    r = await client.get("/v1/orders", headers=auth_header(token))
    assert r.status_code == 403


async def test_list_empty(client: AsyncClient, use_stub_provider: None) -> None:
    token = await register_verified(client, email="empty-orders@example.com")
    r = await client.get("/v1/orders", headers=auth_header(token))
    assert r.status_code == 200
    body = r.json()
    assert body == {"data": [], "next_cursor": None}


async def test_list_after_checkout(client: AsyncClient, use_stub_provider: None) -> None:
    token, order_id = await checkout_as(client, email="one-order@example.com", slug="lamp")
    r = await client.get("/v1/orders", headers=auth_header(token))
    assert r.status_code == 200
    data = r.json()["data"]
    assert len(data) == 1
    assert data[0]["id"] == order_id
    assert data[0]["status"] == "pending_payment"
    assert data[0]["item_count"] == 1


async def test_list_pagination_with_cursor(client: AsyncClient, use_stub_provider: None) -> None:
    token = await register_verified(client, email="many@example.com")
    # Create 3 orders by using 3 distinct products (cart is cleared after checkout).
    ids: list[str] = []
    for i in range(3):
        pid = await seed_product(slug=f"many-{i}")
        await client.post(
            "/v1/cart/items",
            headers=auth_header(token),
            json={"product_id": pid, "quantity": 1, "selections": []},
        )
        r = await client.post(
            "/v1/checkout",
            headers=auth_header(token),
            json={"shipping_address": SHIPPING, "shipping_method": "pickup"},
        )
        ids.append(r.json()["order_id"])

    first = await client.get("/v1/orders?limit=2", headers=auth_header(token))
    assert first.status_code == 200
    first_body = first.json()
    assert len(first_body["data"]) == 2
    assert first_body["next_cursor"] is not None

    # Sorted DESC by placed_at: newest first.
    assert first_body["data"][0]["id"] == ids[2]
    assert first_body["data"][1]["id"] == ids[1]

    second = await client.get(
        f"/v1/orders?limit=2&cursor={first_body['next_cursor']}",
        headers=auth_header(token),
    )
    assert second.status_code == 200
    assert [o["id"] for o in second.json()["data"]] == [ids[0]]


async def test_detail_ok(client: AsyncClient, use_stub_provider: None) -> None:
    token, order_id = await checkout_as(client, email="detail@example.com", slug="ring")
    r = await client.get(f"/v1/orders/{order_id}", headers=auth_header(token))
    assert r.status_code == 200
    order = r.json()["order"]
    assert order["id"] == order_id
    assert order["shipping_method"] == "pickup"
    assert order["shipping_address"]["city"] == "CABA"
    assert len(order["items"]) == 1
    assert order["items"][0]["product_name_snapshot"].startswith("Product")


async def test_cannot_read_other_users_order(client: AsyncClient, use_stub_provider: None) -> None:
    _, order_id = await checkout_as(client, email="owner@example.com", slug="cup")
    other_token = await register_verified(client, email="other@example.com")
    r = await client.get(f"/v1/orders/{order_id}", headers=auth_header(other_token))
    assert r.status_code == 404


async def test_detail_missing_returns_404(client: AsyncClient, use_stub_provider: None) -> None:
    token = await register_verified(client, email="nf@example.com")
    r = await client.get("/v1/orders/01HXZNOMATCH01234567890AAA", headers=auth_header(token))
    assert r.status_code == 404
