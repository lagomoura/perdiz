"""Volume-based discount. "10% off if you buy 3+ of this product"."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, Enum, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, ULIDMixin

# Shared enum reused by coupons, automatic_discounts, and volume_discounts.
discount_type_enum = Enum("percentage", "fixed", name="discount_type", create_type=True)


class VolumeDiscount(Base, ULIDMixin):
    __tablename__ = "volume_discounts"
    __table_args__ = (
        CheckConstraint("min_quantity >= 2", name="ck_volume_discounts_min_quantity"),
        CheckConstraint("value > 0", name="ck_volume_discounts_value_positive"),
    )

    product_id: Mapped[str] = mapped_column(
        String(26), ForeignKey("products.id", ondelete="CASCADE"), nullable=False, index=True
    )
    min_quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    type: Mapped[str] = mapped_column(discount_type_enum, nullable=False)
    # Percentage: 1..100. Fixed: centavos ARS.
    value: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
