"""Coupon redemption — records each use of a coupon on a completed order."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, ULIDMixin


class CouponRedemption(Base, ULIDMixin):
    __tablename__ = "coupon_redemptions"

    coupon_id: Mapped[str] = mapped_column(
        String(26), ForeignKey("coupons.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    order_id: Mapped[str] = mapped_column(
        String(26), ForeignKey("orders.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id: Mapped[str | None] = mapped_column(
        String(26), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    redeemed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
