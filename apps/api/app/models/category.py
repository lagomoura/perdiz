"""Category model. Hierarchical (parent_id) but MVP exposes only 1 level."""

from __future__ import annotations

from sqlalchemy import Enum, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, SoftDeleteMixin, TimestampMixin, ULIDMixin

category_status_enum = Enum("active", "archived", name="category_status", create_type=True)


class Category(Base, ULIDMixin, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "categories"
    __table_args__ = (UniqueConstraint("slug", name="uq_categories_slug"),)

    name: Mapped[str] = mapped_column(Text, nullable=False)
    slug: Mapped[str] = mapped_column(Text, nullable=False)
    parent_id: Mapped[str | None] = mapped_column(
        String(26), ForeignKey("categories.id", ondelete="RESTRICT"), nullable=True, index=True
    )
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    image_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    status: Mapped[str] = mapped_column(category_status_enum, nullable=False, default="active")
