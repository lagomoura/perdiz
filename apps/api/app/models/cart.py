"""Cart model — one ``open`` cart per user at a time."""

from __future__ import annotations

from sqlalchemy import Enum, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, ULIDMixin

cart_status_enum = Enum("open", "converted", "abandoned", name="cart_status", create_type=True)


class Cart(Base, ULIDMixin, TimestampMixin):
    __tablename__ = "carts"
    # Partial unique index enforces "at most one cart with status='open' per user".
    __table_args__ = (
        Index(
            "uq_carts_user_open",
            "user_id",
            unique=True,
            postgresql_where="status = 'open'",
        ),
    )

    user_id: Mapped[str] = mapped_column(
        String(26),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    status: Mapped[str] = mapped_column(
        cart_status_enum, nullable=False, default="open", server_default="open"
    )
    coupon_id: Mapped[str | None] = mapped_column(
        String(26),
        ForeignKey("coupons.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
