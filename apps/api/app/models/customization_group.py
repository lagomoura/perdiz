"""Customization group — a set of options attached to a product (e.g. Color)."""

from __future__ import annotations

from typing import Any

from sqlalchemy import Boolean, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, ULIDMixin

# Enum value list is extensible via ALTER TYPE ... ADD VALUE in a later
# migration when a new customization type is introduced (see
# docs/product/customization-model.md).
customization_type_enum = Enum(
    "COLOR",
    "MATERIAL",
    "SIZE",
    "ENGRAVING_TEXT",
    "ENGRAVING_IMAGE",
    "USER_FILE",
    name="customization_type",
    create_type=True,
)

customization_selection_enum = Enum(
    "single", "multiple", name="customization_selection", create_type=True
)


class CustomizationGroup(Base, ULIDMixin, TimestampMixin):
    __tablename__ = "customization_groups"

    product_id: Mapped[str] = mapped_column(
        String(26), ForeignKey("products.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(Text, nullable=False)
    type: Mapped[str] = mapped_column(customization_type_enum, nullable=False)
    required: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )
    selection_mode: Mapped[str] = mapped_column(customization_selection_enum, nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    # Per-type constraints (max_length, max_size_mb, allowed_mime, ...).
    group_metadata: Mapped[dict[str, Any]] = mapped_column(
        "metadata", JSONB, nullable=False, server_default="{}"
    )
