"""Coupon model. Reuses ``discount_type`` enum from the catalog."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Enum,
    Integer,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, ULIDMixin
from app.models.volume_discount import discount_type_enum

coupon_status_enum = Enum("active", "disabled", name="coupon_status", create_type=True)


class Coupon(Base, ULIDMixin, TimestampMixin):
    __tablename__ = "coupons"
    __table_args__ = (
        UniqueConstraint("code", name="uq_coupons_code"),
        CheckConstraint("value > 0", name="ck_coupons_value_positive"),
        CheckConstraint("min_order_cents >= 0", name="ck_coupons_min_order_non_negative"),
        CheckConstraint(
            "max_uses_total IS NULL OR max_uses_total > 0",
            name="ck_coupons_max_uses_total_positive",
        ),
        CheckConstraint(
            "max_uses_per_user IS NULL OR max_uses_per_user > 0",
            name="ck_coupons_max_uses_per_user_positive",
        ),
    )

    # Stored lowercase so comparisons stay case-insensitive.
    code: Mapped[str] = mapped_column(Text, nullable=False)
    type: Mapped[str] = mapped_column(discount_type_enum, nullable=False)
    value: Mapped[int] = mapped_column(Integer, nullable=False)
    min_order_cents: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    valid_from: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    valid_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    max_uses_total: Mapped[int | None] = mapped_column(Integer, nullable=True)
    max_uses_per_user: Mapped[int | None] = mapped_column(Integer, nullable=True)
    applicable_category_ids: Mapped[list[str]] = mapped_column(
        ARRAY(Text), nullable=False, server_default="{}"
    )
    applicable_product_ids: Mapped[list[str]] = mapped_column(
        ARRAY(Text), nullable=False, server_default="{}"
    )
    stacks_with_automatic: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )
    status: Mapped[str] = mapped_column(
        coupon_status_enum, nullable=False, default="active", server_default="active"
    )
