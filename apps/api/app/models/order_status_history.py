"""Order status history — append-only log of status transitions."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, ULIDMixin
from app.models.order import order_status_enum


class OrderStatusHistory(Base, ULIDMixin):
    __tablename__ = "order_status_history"

    order_id: Mapped[str] = mapped_column(
        String(26), ForeignKey("orders.id", ondelete="CASCADE"), nullable=False, index=True
    )
    from_status: Mapped[str | None] = mapped_column(order_status_enum, nullable=True)
    to_status: Mapped[str] = mapped_column(order_status_enum, nullable=False)
    changed_by: Mapped[str | None] = mapped_column(
        String(26), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    changed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
