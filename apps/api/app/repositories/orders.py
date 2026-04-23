"""Order + payment repository."""

from __future__ import annotations

import base64
from datetime import datetime
from typing import Any

from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions import ValidationError
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


async def list_for_user(
    db: AsyncSession,
    *,
    user_id: str,
    limit: int,
    cursor: str | None,
) -> list[Order]:
    """Paginated ``placed_at DESC`` + ``id DESC`` scan. Cursor encodes the
    last row's ``(placed_at, id)`` so repeated rows at the same millisecond
    don't get duplicated on the boundary.
    """
    stmt = select(Order).where(Order.user_id == user_id)
    if cursor:
        cursor_placed_at, cursor_order_id = _decode_cursor(cursor)
        stmt = stmt.where(
            or_(
                Order.placed_at < cursor_placed_at,
                and_(Order.placed_at == cursor_placed_at, Order.id < cursor_order_id),
            )
        )
    stmt = stmt.order_by(Order.placed_at.desc(), Order.id.desc()).limit(limit)
    return list((await db.execute(stmt)).scalars().all())


async def get_for_user(db: AsyncSession, *, order_id: str, user_id: str) -> Order | None:
    row = await db.execute(select(Order).where(Order.id == order_id, Order.user_id == user_id))
    return row.scalar_one_or_none()


async def list_admin(
    db: AsyncSession,
    *,
    status: str | None,
    user_id: str | None,
    limit: int,
    cursor: str | None,
) -> list[Order]:
    stmt = select(Order)
    if status:
        stmt = stmt.where(Order.status == status)
    if user_id:
        stmt = stmt.where(Order.user_id == user_id)
    if cursor:
        cursor_placed_at, cursor_order_id = _decode_cursor(cursor)
        stmt = stmt.where(
            or_(
                Order.placed_at < cursor_placed_at,
                and_(Order.placed_at == cursor_placed_at, Order.id < cursor_order_id),
            )
        )
    stmt = stmt.order_by(Order.placed_at.desc(), Order.id.desc()).limit(limit)
    return list((await db.execute(stmt)).scalars().all())


async def list_payments_for_order(db: AsyncSession, order_id: str) -> list[Payment]:
    rows = await db.execute(
        select(Payment).where(Payment.order_id == order_id).order_by(Payment.created_at.desc())
    )
    return list(rows.scalars().all())


async def list_status_history(db: AsyncSession, order_id: str) -> list[OrderStatusHistory]:
    rows = await db.execute(
        select(OrderStatusHistory)
        .where(OrderStatusHistory.order_id == order_id)
        .order_by(OrderStatusHistory.changed_at.asc())
    )
    return list(rows.scalars().all())


def encode_cursor(order: Order) -> str:
    raw = f"{order.placed_at.isoformat()}|{order.id}"
    return base64.urlsafe_b64encode(raw.encode()).decode().rstrip("=")


def _decode_cursor(cursor: str) -> tuple[datetime, str]:
    padding = "=" * (-len(cursor) % 4)
    try:
        raw = base64.urlsafe_b64decode(cursor + padding).decode()
        placed_at_iso, order_id = raw.split("|", 1)
        placed_at = datetime.fromisoformat(placed_at_iso)
    except (ValueError, UnicodeDecodeError) as exc:
        raise ValidationError("cursor inválido", details={"field": "cursor"}) from exc
    return placed_at, order_id


async def record_coupon_redemption(
    db: AsyncSession, *, coupon_id: str, order_id: str, user_id: str | None
) -> CouponRedemption:
    redemption = CouponRedemption(coupon_id=coupon_id, order_id=order_id, user_id=user_id)
    db.add(redemption)
    await db.flush()
    return redemption
