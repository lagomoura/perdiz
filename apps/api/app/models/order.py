"""Order model."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, ULIDMixin

order_status_enum = Enum(
    "pending_payment",
    "paid",
    "queued",
    "printing",
    "shipped",
    "delivered",
    "cancelled",
    "refunded",
    name="order_status",
    create_type=True,
)

shipping_method_enum = Enum("pickup", "standard", name="shipping_method", create_type=True)


class Order(Base, ULIDMixin):
    __tablename__ = "orders"
    __table_args__ = (
        CheckConstraint("subtotal_cents >= 0", name="ck_orders_subtotal_non_negative"),
        CheckConstraint("discount_cents >= 0", name="ck_orders_discount_non_negative"),
        CheckConstraint("shipping_cents >= 0", name="ck_orders_shipping_non_negative"),
        CheckConstraint("total_cents >= 0", name="ck_orders_total_non_negative"),
    )

    user_id: Mapped[str] = mapped_column(
        String(26),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    status: Mapped[str] = mapped_column(
        order_status_enum, nullable=False, default="pending_payment"
    )
    subtotal_cents: Mapped[int] = mapped_column(Integer, nullable=False)
    discount_cents: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    shipping_cents: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    total_cents: Mapped[int] = mapped_column(Integer, nullable=False)
    currency: Mapped[str] = mapped_column(
        String(3), nullable=False, default="ARS", server_default="ARS"
    )
    coupon_id: Mapped[str | None] = mapped_column(
        String(26),
        ForeignKey("coupons.id", ondelete="SET NULL"),
        nullable=True,
    )
    # Immutable snapshot of the shipping address at checkout time so a later
    # address edit on the user profile doesn't alter historical orders.
    shipping_address_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    shipping_method: Mapped[str] = mapped_column(shipping_method_enum, nullable=False)
    admin_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    placed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    shipped_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    refunded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
