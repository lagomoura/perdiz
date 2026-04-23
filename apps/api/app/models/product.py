"""Product model."""

from __future__ import annotations

from sqlalchemy import (
    CheckConstraint,
    Computed,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import ARRAY, TSVECTOR
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, SoftDeleteMixin, TimestampMixin, ULIDMixin

stock_mode_enum = Enum("stocked", "print_on_demand", name="stock_mode", create_type=True)
product_status_enum = Enum("draft", "active", "archived", name="product_status", create_type=True)

# Maintained automatically by Postgres as a STORED generated column.
# Uses Spanish dictionary for full-text search; weights name > description > tags.
# Name + description only. Tags live in a GIN index on the array column
# because ``array_to_string`` over polymorphic arrays is not considered
# immutable by Postgres in generated STORED columns.
_SEARCH_TSV_EXPRESSION = (
    "setweight(to_tsvector('spanish'::regconfig, coalesce(name, '')), 'A') || "
    "setweight(to_tsvector('spanish'::regconfig, coalesce(description, '')), 'B')"
)


class Product(Base, ULIDMixin, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "products"
    __table_args__ = (
        UniqueConstraint("slug", name="uq_products_slug"),
        UniqueConstraint("sku", name="uq_products_sku"),
        CheckConstraint("base_price_cents >= 0", name="ck_products_base_price_non_negative"),
        CheckConstraint(
            "stock_quantity IS NULL OR stock_quantity >= 0",
            name="ck_products_stock_quantity_non_negative",
        ),
        CheckConstraint(
            "lead_time_days IS NULL OR lead_time_days >= 1",
            name="ck_products_lead_time_positive",
        ),
        # Enforce stock_mode ↔ (stock_quantity | lead_time_days) consistency.
        CheckConstraint(
            "(stock_mode = 'stocked' AND stock_quantity IS NOT NULL "
            "AND lead_time_days IS NULL) "
            "OR (stock_mode = 'print_on_demand' AND lead_time_days IS NOT NULL "
            "AND stock_quantity IS NULL)",
            name="ck_products_stock_mode_consistency",
        ),
    )

    category_id: Mapped[str] = mapped_column(
        String(26), ForeignKey("categories.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(Text, nullable=False)
    slug: Mapped[str] = mapped_column(Text, nullable=False)
    # Rich text HTML, sanitized at the service layer before insertion.
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    base_price_cents: Mapped[int] = mapped_column(Integer, nullable=False)
    stock_mode: Mapped[str] = mapped_column(stock_mode_enum, nullable=False)
    stock_quantity: Mapped[int | None] = mapped_column(Integer, nullable=True)
    lead_time_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    weight_grams: Mapped[int | None] = mapped_column(Integer, nullable=True)
    dimensions_mm: Mapped[list[int] | None] = mapped_column(ARRAY(Integer), nullable=True)
    sku: Mapped[str] = mapped_column(Text, nullable=False)
    tags: Mapped[list[str]] = mapped_column(ARRAY(Text), nullable=False, server_default="{}")
    status: Mapped[str] = mapped_column(
        product_status_enum, nullable=False, default="draft", server_default="draft"
    )
    search_tsv: Mapped[str] = mapped_column(
        TSVECTOR,
        Computed(_SEARCH_TSV_EXPRESSION, persisted=True),
        nullable=True,
    )
    model_file_id: Mapped[str | None] = mapped_column(
        String(26), ForeignKey("media_files.id", ondelete="SET NULL"), nullable=True
    )
