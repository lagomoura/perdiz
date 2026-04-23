"""MercadoPago webhook: signature validation, idempotency, status sync."""

from __future__ import annotations

import json
from collections.abc import Iterator
from datetime import UTC, datetime

import pytest
from app.db.session import AsyncSessionLocal
from app.models.category import Category
from app.models.order import Order
from app.models.order_status_history import OrderStatusHistory
from app.models.payment import Payment
from app.models.product import Product
from app.models.user import User
from app.services.payments import registry
from app.services.payments.stub import STUB_SECRET, StubPaymentProvider, sign_stub_payload
from httpx import AsyncClient
from sqlalchemy import select, update

from tests.integration._helpers import auth_header, register_user

SHIPPING = {
    "full_name": "Ada",
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


async def _checkout(client: AsyncClient, *, email: str = "hook@example.com") -> str:
    token = await register_user(client, email=email)
    await _verify(email)
    async with AsyncSessionLocal() as s:
        cat = Category(name="Cat", slug=f"c-{email}", sort_order=0)
        s.add(cat)
        await s.flush()
        p = Product(
            category_id=cat.id,
            name="Prod",
            slug=f"p-{email}",
            base_price_cents=10_00,
            stock_mode="stocked",
            stock_quantity=5,
            sku=f"SKU-{email}",
            status="active",
        )
        s.add(p)
        await s.commit()
        await s.refresh(p)
        product_id = p.id

    await client.post(
        "/v1/cart/items",
        headers=auth_header(token),
        json={"product_id": product_id, "quantity": 1, "selections": []},
    )
    r = await client.post(
        "/v1/checkout",
        headers=auth_header(token),
        json={"shipping_address": SHIPPING, "shipping_method": "pickup"},
    )
    assert r.status_code == 201, r.text
    return str(r.json()["order_id"])


def _signed_body(event_id: str, order_id: str, *, status: str) -> tuple[bytes, str]:
    body = json.dumps(
        {
            "id": event_id,
            "status": status,
            "provider_payment_id": order_id,
        },
        separators=(",", ":"),
    ).encode()
    return body, sign_stub_payload(body)


# --- Signature ------------------------------------------------------------


async def test_webhook_rejects_missing_signature(client: AsyncClient) -> None:
    r = await client.post("/v1/webhooks/mercadopago", content=b"{}")
    assert r.status_code == 401


async def test_webhook_rejects_invalid_signature(client: AsyncClient) -> None:
    r = await client.post(
        "/v1/webhooks/mercadopago",
        content=b'{"id":"x"}',
        headers={"x-signature": "deadbeef"},
    )
    assert r.status_code == 401


# --- Status sync + idempotency --------------------------------------------


async def test_webhook_approved_moves_order_to_paid(client: AsyncClient) -> None:
    order_id = await _checkout(client, email="paid@example.com")
    body, sig = _signed_body("evt-1", order_id, status="approved")

    r = await client.post(
        "/v1/webhooks/mercadopago",
        content=body,
        headers={"x-signature": sig, "content-type": "application/json"},
    )
    assert r.status_code == 200, r.text

    async with AsyncSessionLocal() as s:
        order = (await s.execute(select(Order).where(Order.id == order_id))).scalar_one()
        payment = (
            await s.execute(select(Payment).where(Payment.order_id == order_id))
        ).scalar_one()
        history = list(
            (
                await s.execute(
                    select(OrderStatusHistory)
                    .where(OrderStatusHistory.order_id == order_id)
                    .order_by(OrderStatusHistory.changed_at)
                )
            )
            .scalars()
            .all()
        )

    assert order.status == "paid"
    assert order.paid_at is not None
    assert payment.status == "approved"
    assert len(payment.raw_webhook_events) == 1
    assert payment.raw_webhook_events[0]["event_id"] == "evt-1"
    assert [h.to_status for h in history] == ["pending_payment", "paid"]


async def test_webhook_is_idempotent(client: AsyncClient) -> None:
    order_id = await _checkout(client, email="idem@example.com")
    body, sig = _signed_body("evt-dup", order_id, status="approved")

    for _ in range(3):
        r = await client.post(
            "/v1/webhooks/mercadopago",
            content=body,
            headers={"x-signature": sig, "content-type": "application/json"},
        )
        assert r.status_code == 200

    async with AsyncSessionLocal() as s:
        payment = (
            await s.execute(select(Payment).where(Payment.order_id == order_id))
        ).scalar_one()
        history_rows = list(
            (
                await s.execute(
                    select(OrderStatusHistory).where(OrderStatusHistory.order_id == order_id)
                )
            )
            .scalars()
            .all()
        )

    assert len(payment.raw_webhook_events) == 1
    # Only 2 rows: initial + paid transition. Duplicate events must not log.
    assert len(history_rows) == 2


async def test_webhook_rejected_cancels_order(client: AsyncClient) -> None:
    order_id = await _checkout(client, email="rej@example.com")
    body, sig = _signed_body("evt-rej", order_id, status="rejected")
    r = await client.post(
        "/v1/webhooks/mercadopago",
        content=body,
        headers={"x-signature": sig, "content-type": "application/json"},
    )
    assert r.status_code == 200

    async with AsyncSessionLocal() as s:
        order = (await s.execute(select(Order).where(Order.id == order_id))).scalar_one()
    assert order.status == "cancelled"
    assert order.cancelled_at is not None


async def test_webhook_unknown_order_ignored(client: AsyncClient) -> None:
    body, sig = _signed_body("evt-unk", "01HXZNOMATCH01234567890AAA", status="approved")
    r = await client.post(
        "/v1/webhooks/mercadopago",
        content=body,
        headers={"x-signature": sig, "content-type": "application/json"},
    )
    assert r.status_code == 200
    assert r.json()["status"] == "ignored"


def test_stub_secret_available() -> None:
    # Guard: tests rely on this being importable.
    assert STUB_SECRET
