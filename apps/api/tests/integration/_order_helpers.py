"""Shared helpers for order/checkout tests."""

from __future__ import annotations

from collections.abc import Iterator
from datetime import UTC, datetime

import pytest
from app.db.session import AsyncSessionLocal
from app.models.category import Category
from app.models.order import Order
from app.models.product import Product
from app.models.user import User
from app.services.payments import registry
from app.services.payments.stub import StubPaymentProvider
from httpx import AsyncClient
from sqlalchemy import update

from tests.integration._helpers import auth_header, register_user

SHIPPING = {
    "full_name": "Ada Lovelace",
    "street": "Rivadavia",
    "street_number": "100",
    "unit": None,
    "city": "CABA",
    "province": "CABA",
    "postal_code": "1000",
    "country": "AR",
    "phone": "+5491100000000",
    "notes": None,
}


@pytest.fixture
def use_stub_provider() -> Iterator[None]:
    registry.set_provider_override("mercadopago", StubPaymentProvider())
    try:
        yield
    finally:
        registry.set_provider_override("mercadopago", None)


async def verify_user(email: str) -> None:
    async with AsyncSessionLocal() as s:
        await s.execute(
            update(User).where(User.email == email).values(email_verified_at=datetime.now(tz=UTC))
        )
        await s.commit()


async def register_verified(client: AsyncClient, *, email: str) -> str:
    token = await register_user(client, email=email)
    await verify_user(email)
    return token


async def seed_product(*, slug: str, price_cents: int = 50_00) -> str:
    async with AsyncSessionLocal() as s:
        cat = Category(name=f"Cat {slug}", slug=f"cat-{slug}", sort_order=0)
        s.add(cat)
        await s.flush()
        p = Product(
            category_id=cat.id,
            name=f"Product {slug}",
            slug=slug,
            base_price_cents=price_cents,
            stock_mode="stocked",
            stock_quantity=20,
            sku=f"SKU-{slug.upper()}",
            status="active",
        )
        s.add(p)
        await s.commit()
        await s.refresh(p)
        return p.id


async def checkout_as(
    client: AsyncClient, *, email: str, slug: str, quantity: int = 1
) -> tuple[str, str]:
    """Register + verify + seed product + cart + checkout. Return ``(token, order_id)``."""
    token = await register_verified(client, email=email)
    product_id = await seed_product(slug=slug)
    r = await client.post(
        "/v1/cart/items",
        headers=auth_header(token),
        json={"product_id": product_id, "quantity": quantity, "selections": []},
    )
    assert r.status_code == 201, r.text
    r = await client.post(
        "/v1/checkout",
        headers=auth_header(token),
        json={"shipping_address": SHIPPING, "shipping_method": "pickup"},
    )
    assert r.status_code == 201, r.text
    return token, r.json()["order_id"]


async def mark_order_paid(order_id: str) -> None:
    """Jump past the webhook by directly flipping the order to ``paid``."""
    async with AsyncSessionLocal() as s:
        await s.execute(
            update(Order)
            .where(Order.id == order_id)
            .values(status="paid", paid_at=datetime.now(tz=UTC))
        )
        await s.commit()
