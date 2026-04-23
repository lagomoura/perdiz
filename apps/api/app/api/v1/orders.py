"""User-facing order history endpoints."""

from __future__ import annotations

from typing import Annotated, cast

from fastapi import APIRouter, Query

from app.api.deps import CurrentVerifiedUser, DbSession
from app.schemas.orders import (
    OrderDetailUserOut,
    OrderItemUserOut,
    OrderStatus,
    OrderSummaryUserOut,
    OrderUserDetailEnvelope,
    OrderUserListOut,
    ShippingMethod,
)
from app.services.orders import service as order_service

router = APIRouter(prefix="/orders", tags=["orders"])


@router.get("", response_model=OrderUserListOut)
async def list_my_orders(
    db: DbSession,
    user: CurrentVerifiedUser,
    limit: Annotated[int, Query(ge=1, le=50)] = 20,
    cursor: Annotated[str | None, Query()] = None,
) -> OrderUserListOut:
    orders, counts, next_cursor = await order_service.list_user_orders(
        db, user=user, limit=limit, cursor=cursor
    )
    data = [
        OrderSummaryUserOut(
            id=o.id,
            status=cast(OrderStatus, o.status),
            total_cents=o.total_cents,
            currency=o.currency,
            placed_at=o.placed_at,
            item_count=counts.get(o.id, 0),
        )
        for o in orders
    ]
    return OrderUserListOut(data=data, next_cursor=next_cursor)


@router.get("/{order_id}", response_model=OrderUserDetailEnvelope)
async def get_my_order(
    order_id: str, db: DbSession, user: CurrentVerifiedUser
) -> OrderUserDetailEnvelope:
    order, items, image_urls = await order_service.get_user_order(db, user=user, order_id=order_id)
    items_dto = [
        OrderItemUserOut(
            id=item.id,
            product_id=item.product_id,
            product_name_snapshot=item.product_name_snapshot,
            image_url=image_urls.get(item.product_id),
            quantity=item.quantity,
            unit_price_cents=item.unit_price_cents,
            modifiers_total_cents=item.modifiers_total_cents,
            line_total_cents=item.line_total_cents,
        )
        for item in items
    ]
    return OrderUserDetailEnvelope(
        order=OrderDetailUserOut(
            id=order.id,
            status=cast(OrderStatus, order.status),
            subtotal_cents=order.subtotal_cents,
            discount_cents=order.discount_cents,
            shipping_cents=order.shipping_cents,
            total_cents=order.total_cents,
            currency=order.currency,
            shipping_method=cast(ShippingMethod, order.shipping_method),
            shipping_address=order.shipping_address_json,
            placed_at=order.placed_at,
            paid_at=order.paid_at,
            shipped_at=order.shipped_at,
            delivered_at=order.delivered_at,
            cancelled_at=order.cancelled_at,
            refunded_at=order.refunded_at,
            items=items_dto,
        )
    )
