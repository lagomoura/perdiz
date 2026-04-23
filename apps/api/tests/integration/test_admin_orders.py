"""Admin orders: list with filters, detail, status transitions, notes, refund."""

from __future__ import annotations

from app.db.session import AsyncSessionLocal
from app.models.audit_log import AuditLog
from app.models.order import Order
from app.models.order_status_history import OrderStatusHistory
from app.models.payment import Payment
from app.models.user import User
from httpx import AsyncClient
from sqlalchemy import select

from tests.integration._helpers import (
    auth_header,
    register_and_promote_admin,
)
from tests.integration._order_helpers import (
    checkout_as,
    mark_order_paid,
    register_verified,
)

# --- AuthZ ---------------------------------------------------------------


async def test_anonymous_blocked(client: AsyncClient) -> None:
    r = await client.get("/v1/admin/orders")
    assert r.status_code == 401


async def test_non_admin_returns_404(client: AsyncClient) -> None:
    token = await register_verified(client, email="u@example.com")
    r = await client.get("/v1/admin/orders", headers=auth_header(token))
    assert r.status_code == 404


# --- List ----------------------------------------------------------------


async def test_list_empty(client: AsyncClient) -> None:
    admin = await register_and_promote_admin(client)
    r = await client.get("/v1/admin/orders", headers=auth_header(admin))
    assert r.status_code == 200
    assert r.json() == {"data": [], "next_cursor": None}


async def test_list_includes_user_email(client: AsyncClient, use_stub_provider: None) -> None:
    await checkout_as(client, email="buyer@example.com", slug="l1")
    admin = await register_and_promote_admin(client)
    r = await client.get("/v1/admin/orders", headers=auth_header(admin))
    assert r.status_code == 200
    data = r.json()["data"]
    assert len(data) == 1
    assert data[0]["user_email"] == "buyer@example.com"
    assert data[0]["status"] == "pending_payment"


async def test_list_filter_by_status(client: AsyncClient, use_stub_provider: None) -> None:
    _, paid_id = await checkout_as(client, email="paid-f@example.com", slug="f1")
    await mark_order_paid(paid_id)
    await checkout_as(client, email="pending-f@example.com", slug="f2")

    admin = await register_and_promote_admin(client)
    r = await client.get("/v1/admin/orders?status=paid", headers=auth_header(admin))
    assert r.status_code == 200
    data = r.json()["data"]
    assert [o["id"] for o in data] == [paid_id]


async def test_list_filter_by_user_id(client: AsyncClient, use_stub_provider: None) -> None:
    _, order_id = await checkout_as(client, email="a@example.com", slug="g1")
    await checkout_as(client, email="b@example.com", slug="g2")

    async with AsyncSessionLocal() as s:
        a_user = (await s.execute(select(User).where(User.email == "a@example.com"))).scalar_one()
        a_user_id = a_user.id

    admin = await register_and_promote_admin(client)
    r = await client.get(f"/v1/admin/orders?user_id={a_user_id}", headers=auth_header(admin))
    assert [o["id"] for o in r.json()["data"]] == [order_id]


# --- Detail --------------------------------------------------------------


async def test_detail_includes_items_payments_history(
    client: AsyncClient, use_stub_provider: None
) -> None:
    _, order_id = await checkout_as(client, email="detail-adm@example.com", slug="d1", quantity=2)
    admin = await register_and_promote_admin(client)
    r = await client.get(f"/v1/admin/orders/{order_id}", headers=auth_header(admin))
    assert r.status_code == 200
    order = r.json()["order"]
    assert order["id"] == order_id
    assert order["user_email"] == "detail-adm@example.com"
    assert len(order["items"]) == 1
    assert order["items"][0]["quantity"] == 2
    assert len(order["payments"]) == 1
    assert order["payments"][0]["provider"] == "mercadopago"
    assert len(order["status_history"]) == 1
    assert order["status_history"][0]["to_status"] == "pending_payment"


async def test_detail_missing_returns_404(client: AsyncClient) -> None:
    admin = await register_and_promote_admin(client)
    r = await client.get(
        "/v1/admin/orders/01HXZNOMATCH01234567890AAA",
        headers=auth_header(admin),
    )
    assert r.status_code == 404


# --- Transitions ---------------------------------------------------------


async def test_transition_paid_to_queued_to_printing_to_shipped_to_delivered(
    client: AsyncClient, use_stub_provider: None
) -> None:
    _, order_id = await checkout_as(client, email="flow@example.com", slug="fl1")
    await mark_order_paid(order_id)

    admin = await register_and_promote_admin(client)
    for target in ("queued", "printing", "shipped", "delivered"):
        r = await client.patch(
            f"/v1/admin/orders/{order_id}/status",
            headers=auth_header(admin),
            json={"to_status": target},
        )
        assert r.status_code == 200, r.text
        assert r.json()["order"]["status"] == target

    # Verify timestamps set on the key transitions.
    async with AsyncSessionLocal() as s:
        order = (await s.execute(select(Order).where(Order.id == order_id))).scalar_one()
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
    assert order.shipped_at is not None
    assert order.delivered_at is not None
    assert [h.to_status for h in history] == [
        "pending_payment",
        "queued",
        "printing",
        "shipped",
        "delivered",
    ]


async def test_transition_invalid_returns_409(client: AsyncClient, use_stub_provider: None) -> None:
    _, order_id = await checkout_as(client, email="bad@example.com", slug="bd1")
    admin = await register_and_promote_admin(client)
    r = await client.patch(
        f"/v1/admin/orders/{order_id}/status",
        headers=auth_header(admin),
        json={"to_status": "delivered"},
    )
    assert r.status_code == 409
    assert "Transición" in r.json()["error"]["message"]


async def test_cancel_from_paid_ok(client: AsyncClient, use_stub_provider: None) -> None:
    _, order_id = await checkout_as(client, email="cancel@example.com", slug="cc1")
    await mark_order_paid(order_id)
    admin = await register_and_promote_admin(client)
    r = await client.patch(
        f"/v1/admin/orders/{order_id}/status",
        headers=auth_header(admin),
        json={"to_status": "cancelled", "note": "cliente lo pidió"},
    )
    assert r.status_code == 200
    assert r.json()["order"]["status"] == "cancelled"


# --- Notes ---------------------------------------------------------------


async def test_update_admin_notes(client: AsyncClient, use_stub_provider: None) -> None:
    _, order_id = await checkout_as(client, email="notes@example.com", slug="n1")
    admin = await register_and_promote_admin(client)
    r = await client.patch(
        f"/v1/admin/orders/{order_id}/notes",
        headers=auth_header(admin),
        json={"admin_notes": "material especial, retiro jueves"},
    )
    assert r.status_code == 200
    assert r.json()["order"]["admin_notes"] == "material especial, retiro jueves"


# --- Refund --------------------------------------------------------------


async def test_refund_from_paid_marks_payment_and_order(
    client: AsyncClient, use_stub_provider: None
) -> None:
    _, order_id = await checkout_as(client, email="ref@example.com", slug="rf1")
    await mark_order_paid(order_id)
    # Pretend the payment was approved by MP so the refund flips it.
    async with AsyncSessionLocal() as s:
        payment = (
            await s.execute(select(Payment).where(Payment.order_id == order_id))
        ).scalar_one()
        payment.status = "approved"
        await s.commit()

    admin = await register_and_promote_admin(client)
    r = await client.post(
        f"/v1/admin/orders/{order_id}/refund",
        headers=auth_header(admin),
        json={"note": "cliente devolvió la pieza"},
    )
    assert r.status_code == 200
    assert r.json()["order"]["status"] == "refunded"

    async with AsyncSessionLocal() as s:
        payment = (
            await s.execute(select(Payment).where(Payment.order_id == order_id))
        ).scalar_one()
        order = (await s.execute(select(Order).where(Order.id == order_id))).scalar_one()
    assert payment.status == "refunded"
    assert order.refunded_at is not None


async def test_refund_from_pending_rejected(client: AsyncClient, use_stub_provider: None) -> None:
    _, order_id = await checkout_as(client, email="ref-bad@example.com", slug="rb1")
    admin = await register_and_promote_admin(client)
    r = await client.post(
        f"/v1/admin/orders/{order_id}/refund",
        headers=auth_header(admin),
        json={"note": "intento inválido"},
    )
    assert r.status_code == 409


# --- Audit ---------------------------------------------------------------


async def test_transition_writes_audit_log(client: AsyncClient, use_stub_provider: None) -> None:
    _, order_id = await checkout_as(client, email="audit@example.com", slug="aud1")
    await mark_order_paid(order_id)
    admin = await register_and_promote_admin(client)
    await client.patch(
        f"/v1/admin/orders/{order_id}/status",
        headers=auth_header(admin),
        json={"to_status": "queued"},
    )
    async with AsyncSessionLocal() as s:
        logs = list(
            (
                await s.execute(
                    select(AuditLog)
                    .where(AuditLog.entity_id == order_id)
                    .order_by(AuditLog.created_at)
                )
            )
            .scalars()
            .all()
        )
    assert any(log.action == "order.transition.queued" for log in logs)
