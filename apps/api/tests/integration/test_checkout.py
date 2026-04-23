"""Checkout flow: happy path + cart validations."""

from __future__ import annotations

from collections.abc import Iterator
from datetime import UTC, datetime

import pytest
from app.db.session import AsyncSessionLocal
from app.models.category import Category
from app.models.order import Order
from app.models.order_item import OrderItem
from app.models.order_status_history import OrderStatusHistory
from app.models.payment import Payment
from app.models.product import Product
from app.models.user import User
from app.services.payments import registry
from app.services.payments.stub import StubPaymentProvider
from httpx import AsyncClient
from sqlalchemy import select, update

from tests.integration._helpers import auth_header, register_user

SHIPPING = {
    "full_name": "Ada Lovelace",
    "street": "Av. Siempre Viva",
    "street_number": "742",
    "unit": "3B",
    "city": "CABA",
    "province": "CABA",
    "postal_code": "1000",
    "country": "AR",
    "phone": "+5491122334455",
    "notes": None,
}


@pytest.fixture(autouse=True)
def _use_stub_provider() -> Iterator[None]:
    registry.set_provider_override("mercadopago", StubPaymentProvider())
    try:
        yield
    finally:
        registry.set_provider_override("mercadopago", None)


async def _verify(email: str) -> None:
    async with AsyncSessionLocal() as s:
        await s.execute(
            update(User).where(User.email == email).values(email_verified_at=datetime.now(tz=UTC))
        )
        await s.commit()


async def _verified(client: AsyncClient, *, email: str = "checkout@example.com") -> str:
    token = await register_user(client, email=email)
    await _verify(email)
    return token


async def _seed_product(*, slug: str = "lamp", price: int = 150_00) -> str:
    async with AsyncSessionLocal() as s:
        cat = Category(name="Decor", slug=f"d-{slug}", sort_order=0)
        s.add(cat)
        await s.flush()
        p = Product(
            category_id=cat.id,
            name=f"Lamp {slug}",
            slug=slug,
            base_price_cents=price,
            stock_mode="stocked",
            stock_quantity=10,
            sku=f"SKU-{slug.upper()}",
            status="active",
        )
        s.add(p)
        await s.commit()
        await s.refresh(p)
        return p.id


async def _add_to_cart(client: AsyncClient, token: str, product_id: str, qty: int = 1) -> None:
    r = await client.post(
        "/v1/cart/items",
        headers=auth_header(token),
        json={"product_id": product_id, "quantity": qty, "selections": []},
    )
    assert r.status_code == 201, r.text


# --- Happy path -----------------------------------------------------------


async def test_checkout_creates_order_and_returns_redirect(client: AsyncClient) -> None:
    token = await _verified(client)
    product_id = await _seed_product()
    await _add_to_cart(client, token, product_id, qty=2)

    r = await client.post(
        "/v1/checkout",
        headers=auth_header(token),
        json={
            "shipping_address": SHIPPING,
            "shipping_method": "standard",
            "payment_provider": "mercadopago",
        },
    )
    assert r.status_code == 201, r.text
    data = r.json()
    assert data["order_id"].startswith(("0", "1", "2", "3", "4", "5", "6", "7", "8", "9"))
    assert data["provider"] == "mercadopago"
    assert data["redirect_url"].startswith("https://stub.local/checkout/")
    # 2 * 150 ARS + 500 ARS shipping = 800 ARS = 80_000 cents
    assert data["total_cents"] == 80_000


async def test_pickup_has_no_shipping_cost(client: AsyncClient) -> None:
    token = await _verified(client, email="pickup@example.com")
    product_id = await _seed_product(slug="mini", price=50_00)
    await _add_to_cart(client, token, product_id)

    r = await client.post(
        "/v1/checkout",
        headers=auth_header(token),
        json={
            "shipping_address": SHIPPING,
            "shipping_method": "pickup",
        },
    )
    assert r.status_code == 201, r.text
    assert r.json()["total_cents"] == 50_00


async def test_checkout_empty_cart_rejected(client: AsyncClient) -> None:
    token = await _verified(client, email="empty@example.com")
    r = await client.post(
        "/v1/checkout",
        headers=auth_header(token),
        json={"shipping_address": SHIPPING, "shipping_method": "pickup"},
    )
    assert r.status_code == 409
    assert "carrito" in r.json()["error"]["message"].lower()


async def test_checkout_converts_cart_so_next_read_is_fresh(client: AsyncClient) -> None:
    token = await _verified(client, email="fresh@example.com")
    product_id = await _seed_product(slug="ring", price=20_00)
    await _add_to_cart(client, token, product_id)

    r = await client.post(
        "/v1/checkout",
        headers=auth_header(token),
        json={"shipping_address": SHIPPING, "shipping_method": "pickup"},
    )
    assert r.status_code == 201

    follow = await client.get("/v1/cart", headers=auth_header(token))
    assert follow.status_code == 200
    body = follow.json()["cart"]
    assert body["items"] == []
    assert body["total_cents"] == 0


async def test_checkout_persists_order_items_snapshot(client: AsyncClient) -> None:
    token = await _verified(client, email="snap@example.com")
    product_id = await _seed_product(slug="cup", price=30_00)
    await _add_to_cart(client, token, product_id, qty=3)

    r = await client.post(
        "/v1/checkout",
        headers=auth_header(token),
        json={"shipping_address": SHIPPING, "shipping_method": "pickup"},
    )
    assert r.status_code == 201
    order_id = r.json()["order_id"]

    async with AsyncSessionLocal() as s:
        order = (await s.execute(select(Order).where(Order.id == order_id))).scalar_one()
        items = list(
            (await s.execute(select(OrderItem).where(OrderItem.order_id == order_id)))
            .scalars()
            .all()
        )
        history = list(
            (
                await s.execute(
                    select(OrderStatusHistory).where(OrderStatusHistory.order_id == order_id)
                )
            )
            .scalars()
            .all()
        )
        payment = (
            await s.execute(select(Payment).where(Payment.order_id == order_id))
        ).scalar_one()

    assert order.status == "pending_payment"
    assert order.total_cents == 90_00
    assert len(items) == 1
    assert items[0].product_name_snapshot.startswith("Lamp")
    assert items[0].quantity == 3
    assert items[0].line_total_cents == 90_00
    assert history[0].to_status == "pending_payment"
    assert payment.provider == "mercadopago"
    assert payment.provider_payment_id.startswith("stub-pref-")
    assert payment.status == "pending"


async def test_checkout_requires_verified_user(client: AsyncClient) -> None:
    token = await register_user(client, email="unverified-chk@example.com")
    r = await client.post(
        "/v1/checkout",
        headers=auth_header(token),
        json={"shipping_address": SHIPPING, "shipping_method": "pickup"},
    )
    assert r.status_code == 403


async def test_checkout_requires_auth(client: AsyncClient) -> None:
    r = await client.post(
        "/v1/checkout",
        json={"shipping_address": SHIPPING, "shipping_method": "pickup"},
    )
    assert r.status_code == 401
