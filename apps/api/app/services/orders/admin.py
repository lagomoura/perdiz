"""Admin order mutations + queries."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions import NotFoundError
from app.models.order import Order
from app.models.order_item import OrderItem
from app.models.order_status_history import OrderStatusHistory
from app.models.payment import Payment
from app.models.user import User
from app.repositories import orders as orders_repo
from app.services import audit
from app.services.emails import orders as order_emails
from app.services.orders.transitions import (
    assert_refund_allowed,
    assert_transition_allowed,
)

DEFAULT_ADMIN_LIMIT = 50
MAX_ADMIN_LIMIT = 200


@dataclass
class AdminOrderListView:
    orders: list[Order]
    user_emails: dict[str, str]
    next_cursor: str | None


@dataclass
class AdminOrderDetailView:
    order: Order
    user_email: str
    items: list[OrderItem]
    payments: list[Payment]
    status_history: list[OrderStatusHistory]


async def list_orders(
    db: AsyncSession,
    *,
    status: str | None,
    user_id: str | None,
    limit: int,
    cursor: str | None,
) -> AdminOrderListView:
    capped = max(1, min(limit, MAX_ADMIN_LIMIT))
    orders = await orders_repo.list_admin(
        db,
        status=status,
        user_id=user_id,
        limit=capped + 1,
        cursor=cursor,
    )
    next_cursor = None
    if len(orders) > capped:
        next_cursor = orders_repo.encode_cursor(orders[capped - 1])
        orders = orders[:capped]
    user_emails = await _fetch_user_emails(db, [o.user_id for o in orders])
    return AdminOrderListView(orders=orders, user_emails=user_emails, next_cursor=next_cursor)


async def get_order_detail(db: AsyncSession, *, order_id: str) -> AdminOrderDetailView:
    order = await orders_repo.get_order(db, order_id)
    if order is None:
        raise NotFoundError("Pedido no encontrado.")
    items = await orders_repo.list_items_for_order(db, order_id)
    payments = await orders_repo.list_payments_for_order(db, order_id)
    history = await orders_repo.list_status_history(db, order_id)
    emails = await _fetch_user_emails(db, [order.user_id])
    return AdminOrderDetailView(
        order=order,
        user_email=emails.get(order.user_id, ""),
        items=items,
        payments=payments,
        status_history=history,
    )


async def transition_status(
    db: AsyncSession,
    *,
    actor: User,
    order_id: str,
    to_status: str,
    note: str | None,
) -> Order:
    order = await orders_repo.get_order(db, order_id)
    if order is None:
        raise NotFoundError("Pedido no encontrado.")
    assert_transition_allowed(order.status, to_status)

    before = audit.snapshot(order)
    previous = order.status
    now = datetime.now(tz=UTC)
    order.status = to_status
    if to_status == "shipped":
        order.shipped_at = now
    elif to_status == "delivered":
        order.delivered_at = now
    elif to_status == "cancelled":
        order.cancelled_at = now

    await orders_repo.create_status_history(
        db,
        order_id=order.id,
        from_status=previous,
        to_status=to_status,
        changed_by=actor.id,
        note=note or f"admin.{to_status}",
    )

    await db.flush()
    await db.refresh(order)
    await audit.log_mutation(
        db,
        actor=actor,
        action=f"order.transition.{to_status}",
        entity_type="order",
        entity_id=order.id,
        before=before,
        after=audit.snapshot(order),
    )
    await db.commit()
    await db.refresh(order)
    await _notify_transition(db, order=order, to_status=to_status)
    return order


async def update_notes(
    db: AsyncSession,
    *,
    actor: User,
    order_id: str,
    admin_notes: str | None,
) -> Order:
    order = await orders_repo.get_order(db, order_id)
    if order is None:
        raise NotFoundError("Pedido no encontrado.")
    before = audit.snapshot(order)
    order.admin_notes = admin_notes
    await db.flush()
    await db.refresh(order)
    await audit.log_mutation(
        db,
        actor=actor,
        action="order.notes.update",
        entity_type="order",
        entity_id=order.id,
        before=before,
        after=audit.snapshot(order),
    )
    await db.commit()
    await db.refresh(order)
    return order


async def refund_order(
    db: AsyncSession,
    *,
    actor: User,
    order_id: str,
    note: str,
) -> Order:
    """Mark an order and its latest payment as refunded.

    This PR only records the intent + audit trail. Calling the payment
    provider's refund API lives in the later payments-ops PR; it needs
    access to the provider's secret which is out-of-scope here.
    """
    order = await orders_repo.get_order(db, order_id)
    if order is None:
        raise NotFoundError("Pedido no encontrado.")
    assert_refund_allowed(order.status)

    before = audit.snapshot(order)
    previous = order.status
    order.status = "refunded"
    order.refunded_at = datetime.now(tz=UTC)

    payments = await orders_repo.list_payments_for_order(db, order_id)
    for payment in payments:
        if payment.status == "approved":
            payment.status = "refunded"

    await orders_repo.create_status_history(
        db,
        order_id=order.id,
        from_status=previous,
        to_status="refunded",
        changed_by=actor.id,
        note=f"admin.refund: {note}",
    )

    await db.flush()
    await db.refresh(order)
    await audit.log_mutation(
        db,
        actor=actor,
        action="order.refund",
        entity_type="order",
        entity_id=order.id,
        before=before,
        after=audit.snapshot(order),
    )
    await db.commit()
    await db.refresh(order)
    await _notify_transition(db, order=order, to_status="refunded")
    return order


async def _notify_transition(db: AsyncSession, *, order: Order, to_status: str) -> None:
    user = await db.get(User, order.user_id)
    if user is None:
        return
    if to_status == "shipped":
        await order_emails.send_order_shipped(to=user.email, order=order)
    elif to_status == "cancelled":
        await order_emails.send_order_cancelled(to=user.email, order=order)
    elif to_status == "refunded":
        await order_emails.send_order_refunded(to=user.email, order=order)


async def _fetch_user_emails(db: AsyncSession, user_ids: list[str]) -> dict[str, str]:
    if not user_ids:
        return {}
    rows = await db.execute(select(User.id, User.email).where(User.id.in_(set(user_ids))))
    return {uid: email for uid, email in rows.all()}
