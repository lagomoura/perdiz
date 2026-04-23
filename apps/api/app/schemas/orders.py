"""Order schemas — user-facing + admin views.

Split from ``checkout.py`` because order read endpoints outgrew the
checkout response and the admin view carries data (customer email,
payment history) that should never leak to the user-facing serializer.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

OrderStatus = Literal[
    "pending_payment",
    "paid",
    "queued",
    "printing",
    "shipped",
    "delivered",
    "cancelled",
    "refunded",
]

ShippingMethod = Literal["pickup", "standard"]


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)


# --- User-facing ---------------------------------------------------------


class OrderItemUserOut(_Strict):
    id: str
    product_id: str
    product_name_snapshot: str
    image_url: str | None
    quantity: int
    unit_price_cents: int
    modifiers_total_cents: int
    line_total_cents: int


class OrderSummaryUserOut(_Strict):
    id: str
    status: OrderStatus
    total_cents: int
    currency: str
    placed_at: datetime
    item_count: int


class OrderDetailUserOut(_Strict):
    id: str
    status: OrderStatus
    subtotal_cents: int
    discount_cents: int
    shipping_cents: int
    total_cents: int
    currency: str
    shipping_method: ShippingMethod
    shipping_address: dict[str, Any]
    placed_at: datetime
    paid_at: datetime | None
    shipped_at: datetime | None
    delivered_at: datetime | None
    cancelled_at: datetime | None
    refunded_at: datetime | None
    items: list[OrderItemUserOut]


class OrderUserListOut(_Strict):
    data: list[OrderSummaryUserOut]
    next_cursor: str | None = None


class OrderUserDetailEnvelope(_Strict):
    order: OrderDetailUserOut


# --- Admin ---------------------------------------------------------------


class AdminStatusHistoryEntry(_Strict):
    from_status: OrderStatus | None
    to_status: OrderStatus
    changed_by_user_id: str | None
    note: str | None
    changed_at: datetime


class AdminPaymentOut(_Strict):
    id: str
    provider: Literal["mercadopago", "stripe", "paypal"]
    provider_payment_id: str
    status: Literal["pending", "approved", "rejected", "refunded"]
    amount_cents: int
    currency: str
    created_at: datetime
    updated_at: datetime


class AdminOrderItemOut(_Strict):
    id: str
    product_id: str
    product_name_snapshot: str
    quantity: int
    unit_price_cents: int
    modifiers_total_cents: int
    line_total_cents: int
    customizations: dict[str, Any]


class AdminOrderSummary(_Strict):
    id: str
    user_id: str
    user_email: str
    status: OrderStatus
    total_cents: int
    currency: str
    placed_at: datetime
    paid_at: datetime | None


class AdminOrderDetail(_Strict):
    id: str
    user_id: str
    user_email: str
    status: OrderStatus
    subtotal_cents: int
    discount_cents: int
    shipping_cents: int
    total_cents: int
    currency: str
    coupon_id: str | None
    shipping_method: ShippingMethod
    shipping_address: dict[str, Any]
    admin_notes: str | None
    placed_at: datetime
    paid_at: datetime | None
    shipped_at: datetime | None
    delivered_at: datetime | None
    cancelled_at: datetime | None
    refunded_at: datetime | None
    items: list[AdminOrderItemOut]
    payments: list[AdminPaymentOut]
    status_history: list[AdminStatusHistoryEntry]


class AdminOrderListOut(_Strict):
    data: list[AdminOrderSummary]
    next_cursor: str | None = None


class AdminOrderDetailOut(_Strict):
    order: AdminOrderDetail


# --- Admin mutation payloads ---------------------------------------------


class AdminStatusTransitionIn(_Strict):
    to_status: Literal["queued", "printing", "shipped", "delivered", "cancelled"]
    note: str | None = Field(default=None, max_length=500)


class AdminOrderNotesIn(_Strict):
    admin_notes: str | None = Field(default=None, max_length=2000)


class AdminRefundIn(_Strict):
    note: str = Field(min_length=1, max_length=500)
