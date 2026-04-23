"""Cart item — line in a cart.

``unit_price_cents`` and ``modifiers_total_cents`` are **snapshots** at
add time. They let the cart survive product price changes with a clear
warning path at checkout; the user's shown total equals what we'll
charge unless they re-add.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, ULIDMixin


class CartItem(Base, ULIDMixin):
    __tablename__ = "cart_items"
    __table_args__ = (
        CheckConstraint("quantity BETWEEN 1 AND 20", name="ck_cart_items_quantity_range"),
        CheckConstraint("unit_price_cents >= 0", name="ck_cart_items_unit_price_non_negative"),
    )

    cart_id: Mapped[str] = mapped_column(
        String(26), ForeignKey("carts.id", ondelete="CASCADE"), nullable=False, index=True
    )
    product_id: Mapped[str] = mapped_column(
        String(26), ForeignKey("products.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    unit_price_cents: Mapped[int] = mapped_column(Integer, nullable=False)
    modifiers_total_cents: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    # Shape of ``customizations``: see docs/product/customization-model.md.
    # ``{"selections": [...], "resolved_modifier_cents": int, "snapshot_version": int}``
    customizations: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, server_default="{}"
    )
    added_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
