"""Customization option — a single pick within a customization group.

For types without predefined options (ENGRAVING_TEXT, ENGRAVING_IMAGE,
USER_FILE) a single virtual option row is created that holds the
``price_modifier_cents``.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import Boolean, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, ULIDMixin


class CustomizationOption(Base, ULIDMixin, TimestampMixin):
    __tablename__ = "customization_options"

    group_id: Mapped[str] = mapped_column(
        String(26),
        ForeignKey("customization_groups.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    label: Mapped[str] = mapped_column(Text, nullable=False)
    price_modifier_cents: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    is_default: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )
    is_available: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="true"
    )
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    # Type-specific payload: {"hex": "#FF0000"} for COLOR, {"dimensions_mm": [...]} for SIZE, etc.
    option_metadata: Mapped[dict[str, Any]] = mapped_column(
        "metadata", JSONB, nullable=False, server_default="{}"
    )
