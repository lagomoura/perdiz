"""Automatic discount applied to a category or a single product without a coupon code."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, Enum, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, ULIDMixin
from app.models.volume_discount import discount_type_enum

discount_scope_enum = Enum("category", "product", name="discount_scope", create_type=True)

discount_status_enum = Enum("active", "disabled", name="discount_status", create_type=True)


class AutomaticDiscount(Base, ULIDMixin, TimestampMixin):
    __tablename__ = "automatic_discounts"
    __table_args__ = (CheckConstraint("value > 0", name="ck_automatic_discounts_value_positive"),)

    name: Mapped[str] = mapped_column(Text, nullable=False)
    type: Mapped[str] = mapped_column(discount_type_enum, nullable=False)
    value: Mapped[int] = mapped_column(Integer, nullable=False)
    scope: Mapped[str] = mapped_column(discount_scope_enum, nullable=False)
    # FK is not enforced at the DB level because target can point to either
    # categories or products depending on scope. Validation lives in the service.
    target_id: Mapped[str] = mapped_column(String(26), nullable=False, index=True)
    valid_from: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    valid_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(
        discount_status_enum, nullable=False, default="active", server_default="active"
    )
