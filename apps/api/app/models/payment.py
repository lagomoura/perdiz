"""Payment — one row per external payment-provider attempt on an Order."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, ULIDMixin

payment_provider_enum = Enum(
    "mercadopago", "stripe", "paypal", name="payment_provider", create_type=True
)
payment_status_enum = Enum(
    "pending", "approved", "rejected", "refunded", name="payment_status", create_type=True
)


class Payment(Base, ULIDMixin):
    __tablename__ = "payments"
    __table_args__ = (
        UniqueConstraint("provider", "provider_payment_id", name="uq_payments_provider_ref"),
    )

    order_id: Mapped[str] = mapped_column(
        String(26), ForeignKey("orders.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    provider: Mapped[str] = mapped_column(payment_provider_enum, nullable=False)
    # Blank at creation, filled after the provider returns an intent / checkout id.
    provider_payment_id: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(
        payment_status_enum, nullable=False, default="pending", server_default="pending"
    )
    amount_cents: Mapped[int] = mapped_column(Integer, nullable=False)
    currency: Mapped[str] = mapped_column(
        String(3), nullable=False, default="ARS", server_default="ARS"
    )
    # Append-only list of webhook events received. The event id is used for
    # idempotency: a webhook with an id we've already seen is rejected.
    raw_webhook_events: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONB, nullable=False, server_default="[]"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
