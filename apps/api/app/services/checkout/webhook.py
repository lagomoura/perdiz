"""Webhook processing for payment providers.

Idempotency: each ``Payment`` keeps an append-only list of normalised
webhook events. If the incoming ``event_id`` is already present we
return silently — MercadoPago retries aggressively and we'd double-move
an order to ``paid`` otherwise.
"""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import flag_modified

from app.exceptions import NotFoundError
from app.models.order import Order
from app.models.payment import Payment
from app.repositories import orders as orders_repo
from app.services.payments.base import WebhookEvent


async def process_event(db: AsyncSession, *, provider_name: str, event: WebhookEvent) -> Payment:
    # provider_payment_id carries our external_reference (= order id) for
    # MercadoPago; that's what the provider normalised into ``WebhookEvent``.
    order = await orders_repo.get_order(db, event.provider_payment_id)
    if order is None:
        raise NotFoundError("order not found for webhook")

    payment = await _find_payment_for_order(db, order=order, provider_name=provider_name)
    if payment is None:
        raise NotFoundError("payment not found for webhook")

    if _is_duplicate(payment, event.event_id):
        return payment

    payment.raw_webhook_events = [
        *payment.raw_webhook_events,
        {
            "event_id": event.event_id,
            "status": event.status,
            "received_at": datetime.now(tz=UTC).isoformat(),
            "payload": event.raw,
        },
    ]
    flag_modified(payment, "raw_webhook_events")
    payment.status = event.status

    await _sync_order_status(db, order=order, payment_status=event.status)
    await db.commit()
    return payment


async def _find_payment_for_order(
    db: AsyncSession, *, order: Order, provider_name: str
) -> Payment | None:
    row = await db.execute(
        select(Payment)
        .where(Payment.order_id == order.id, Payment.provider == provider_name)
        .order_by(Payment.created_at.desc())
        .limit(1)
    )
    return row.scalar_one_or_none()


def _is_duplicate(payment: Payment, event_id: str) -> bool:
    return any(evt.get("event_id") == event_id for evt in payment.raw_webhook_events)


async def _sync_order_status(db: AsyncSession, *, order: Order, payment_status: str) -> None:
    target: str | None = None
    if payment_status == "approved" and order.status == "pending_payment":
        target = "paid"
    elif payment_status == "rejected" and order.status == "pending_payment":
        target = "cancelled"
    elif payment_status == "refunded" and order.status in {"paid", "queued", "printing"}:
        target = "refunded"
    if target is None:
        return

    now = datetime.now(tz=UTC)
    previous = order.status
    order.status = target
    if target == "paid":
        order.paid_at = now
    elif target == "cancelled":
        order.cancelled_at = now
    elif target == "refunded":
        order.refunded_at = now

    await orders_repo.create_status_history(
        db,
        order_id=order.id,
        from_status=previous,
        to_status=target,
        changed_by=None,
        note=f"webhook.{payment_status}",
    )
