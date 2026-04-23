"""Order + payment repository."""

from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.coupon_redemption import CouponRedemption
from app.models.order import Order
from app.models.order_item import OrderItem
from app.models.order_status_history import OrderStatusHistory
from app.models.payment import Payment


async def create_order(db: AsyncSession, **fields: Any) -> Order:
    order = Order(**fields)
    db.add(order)
    await db.flush()
    await db.refresh(order)
    return order


async def create_item(db: AsyncSession, **fields: Any) -> OrderItem:
    item = OrderItem(**fields)
    db.add(item)
    await db.flush()
    return item


async def create_status_history(
    db: AsyncSession,
    *,
    order_id: str,
    from_status: str | None,
    to_status: str,
    changed_by: str | None,
    note: str | None = None,
) -> OrderStatusHistory:
    entry = OrderStatusHistory(
        order_id=order_id,
        from_status=from_status,
        to_status=to_status,
        changed_by=changed_by,
        note=note,
    )
    db.add(entry)
    await db.flush()
    return entry


async def create_payment(db: AsyncSession, **fields: Any) -> Payment:
    payment = Payment(**fields)
    db.add(payment)
    await db.flush()
    await db.refresh(payment)
    return payment


async def get_payment_by_provider_ref(
    db: AsyncSession, *, provider: str, provider_payment_id: str
) -> Payment | None:
    row = await db.execute(
        select(Payment).where(
            Payment.provider == provider,
            Payment.provider_payment_id == provider_payment_id,
        )
    )
    return row.scalar_one_or_none()


async def get_order(db: AsyncSession, order_id: str) -> Order | None:
    return await db.get(Order, order_id)


async def list_items_for_order(db: AsyncSession, order_id: str) -> list[OrderItem]:
    rows = await db.execute(
        select(OrderItem).where(OrderItem.order_id == order_id).order_by(OrderItem.id)
    )
    return list(rows.scalars().all())


async def record_coupon_redemption(
    db: AsyncSession, *, coupon_id: str, order_id: str, user_id: str | None
) -> CouponRedemption:
    redemption = CouponRedemption(coupon_id=coupon_id, order_id=order_id, user_id=user_id)
    db.add(redemption)
    await db.flush()
    return redemption
