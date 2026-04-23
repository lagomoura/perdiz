"""Admin orders — list, detail, status transitions, notes, refund."""

from __future__ import annotations

from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query

from app.api.deps import DbSession, require_role
from app.models.user import User
from app.schemas.orders import (
    AdminOrderDetail,
    AdminOrderDetailOut,
    AdminOrderItemOut,
    AdminOrderListOut,
    AdminOrderNotesIn,
    AdminOrderSummary,
    AdminPaymentOut,
    AdminRefundIn,
    AdminStatusHistoryEntry,
    AdminStatusTransitionIn,
)
from app.services.orders import admin as admin_service

router = APIRouter(
    prefix="/admin/orders",
    tags=["admin-orders"],
    dependencies=[Depends(require_role("admin"))],
)


OrderStatusFilter = Literal[
    "pending_payment",
    "paid",
    "queued",
    "printing",
    "shipped",
    "delivered",
    "cancelled",
    "refunded",
]


def _serialize_summary(order, email: str) -> AdminOrderSummary:  # type: ignore[no-untyped-def]
    return AdminOrderSummary(
        id=order.id,
        user_id=order.user_id,
        user_email=email,
        status=order.status,
        total_cents=order.total_cents,
        currency=order.currency,
        placed_at=order.placed_at,
        paid_at=order.paid_at,
    )


def _serialize_detail(view) -> AdminOrderDetail:  # type: ignore[no-untyped-def]
    o = view.order
    return AdminOrderDetail(
        id=o.id,
        user_id=o.user_id,
        user_email=view.user_email,
        status=o.status,
        subtotal_cents=o.subtotal_cents,
        discount_cents=o.discount_cents,
        shipping_cents=o.shipping_cents,
        total_cents=o.total_cents,
        currency=o.currency,
        coupon_id=o.coupon_id,
        shipping_method=o.shipping_method,
        shipping_address=o.shipping_address_json,
        admin_notes=o.admin_notes,
        placed_at=o.placed_at,
        paid_at=o.paid_at,
        shipped_at=o.shipped_at,
        delivered_at=o.delivered_at,
        cancelled_at=o.cancelled_at,
        refunded_at=o.refunded_at,
        items=[
            AdminOrderItemOut(
                id=item.id,
                product_id=item.product_id,
                product_name_snapshot=item.product_name_snapshot,
                quantity=item.quantity,
                unit_price_cents=item.unit_price_cents,
                modifiers_total_cents=item.modifiers_total_cents,
                line_total_cents=item.line_total_cents,
                customizations=item.customizations,
            )
            for item in view.items
        ],
        payments=[
            AdminPaymentOut(
                id=p.id,
                provider=p.provider,
                provider_payment_id=p.provider_payment_id,
                status=p.status,
                amount_cents=p.amount_cents,
                currency=p.currency,
                created_at=p.created_at,
                updated_at=p.updated_at,
            )
            for p in view.payments
        ],
        status_history=[
            AdminStatusHistoryEntry(
                from_status=h.from_status,
                to_status=h.to_status,
                changed_by_user_id=h.changed_by,
                note=h.note,
                changed_at=h.changed_at,
            )
            for h in view.status_history
        ],
    )


@router.get("", response_model=AdminOrderListOut)
async def list_orders(
    db: DbSession,
    status: Annotated[OrderStatusFilter | None, Query()] = None,
    user_id: Annotated[str | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    cursor: Annotated[str | None, Query()] = None,
) -> AdminOrderListOut:
    view = await admin_service.list_orders(
        db, status=status, user_id=user_id, limit=limit, cursor=cursor
    )
    data = [_serialize_summary(o, view.user_emails.get(o.user_id, "")) for o in view.orders]
    return AdminOrderListOut(data=data, next_cursor=view.next_cursor)


@router.get("/{order_id}", response_model=AdminOrderDetailOut)
async def get_order(order_id: str, db: DbSession) -> AdminOrderDetailOut:
    view = await admin_service.get_order_detail(db, order_id=order_id)
    return AdminOrderDetailOut(order=_serialize_detail(view))


@router.patch("/{order_id}/status", response_model=AdminOrderDetailOut)
async def transition_status(
    order_id: str,
    payload: AdminStatusTransitionIn,
    db: DbSession,
    actor: Annotated[User, Depends(require_role("admin"))],
) -> AdminOrderDetailOut:
    await admin_service.transition_status(
        db,
        actor=actor,
        order_id=order_id,
        to_status=payload.to_status,
        note=payload.note,
    )
    view = await admin_service.get_order_detail(db, order_id=order_id)
    return AdminOrderDetailOut(order=_serialize_detail(view))


@router.patch("/{order_id}/notes", response_model=AdminOrderDetailOut)
async def update_notes(
    order_id: str,
    payload: AdminOrderNotesIn,
    db: DbSession,
    actor: Annotated[User, Depends(require_role("admin"))],
) -> AdminOrderDetailOut:
    await admin_service.update_notes(
        db, actor=actor, order_id=order_id, admin_notes=payload.admin_notes
    )
    view = await admin_service.get_order_detail(db, order_id=order_id)
    return AdminOrderDetailOut(order=_serialize_detail(view))


@router.post("/{order_id}/refund", response_model=AdminOrderDetailOut)
async def refund_order(
    order_id: str,
    payload: AdminRefundIn,
    db: DbSession,
    actor: Annotated[User, Depends(require_role("admin"))],
) -> AdminOrderDetailOut:
    await admin_service.refund_order(db, actor=actor, order_id=order_id, note=payload.note)
    view = await admin_service.get_order_detail(db, order_id=order_id)
    return AdminOrderDetailOut(order=_serialize_detail(view))
