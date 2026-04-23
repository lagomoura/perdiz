"""carts, cart_items, coupons

Revision ID: 0004
Revises: 0003
Create Date: 2026-04-23

"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0004"
down_revision: str | Sequence[str] | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    postgresql.ENUM("open", "converted", "abandoned", name="cart_status").create(
        bind, checkfirst=True
    )
    postgresql.ENUM("active", "disabled", name="coupon_status").create(bind, checkfirst=True)

    # --- coupons (first — carts will FK to it) ---------------------------
    op.create_table(
        "coupons",
        sa.Column("id", sa.String(length=26), primary_key=True),
        sa.Column("code", sa.Text(), nullable=False),
        sa.Column(
            "type",
            postgresql.ENUM("percentage", "fixed", name="discount_type", create_type=False),
            nullable=False,
        ),
        sa.Column("value", sa.Integer(), nullable=False),
        sa.Column("min_order_cents", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("valid_from", sa.DateTime(timezone=True), nullable=True),
        sa.Column("valid_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("max_uses_total", sa.Integer(), nullable=True),
        sa.Column("max_uses_per_user", sa.Integer(), nullable=True),
        sa.Column(
            "applicable_category_ids",
            postgresql.ARRAY(sa.Text()),
            nullable=False,
            server_default=sa.text("ARRAY[]::text[]"),
        ),
        sa.Column(
            "applicable_product_ids",
            postgresql.ARRAY(sa.Text()),
            nullable=False,
            server_default=sa.text("ARRAY[]::text[]"),
        ),
        sa.Column(
            "stacks_with_automatic",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column(
            "status",
            postgresql.ENUM("active", "disabled", name="coupon_status", create_type=False),
            nullable=False,
            server_default="active",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.UniqueConstraint("code", name="uq_coupons_code"),
        sa.CheckConstraint("value > 0", name="ck_coupons_value_positive"),
        sa.CheckConstraint("min_order_cents >= 0", name="ck_coupons_min_order_non_negative"),
        sa.CheckConstraint(
            "max_uses_total IS NULL OR max_uses_total > 0",
            name="ck_coupons_max_uses_total_positive",
        ),
        sa.CheckConstraint(
            "max_uses_per_user IS NULL OR max_uses_per_user > 0",
            name="ck_coupons_max_uses_per_user_positive",
        ),
    )

    # --- carts ------------------------------------------------------------
    op.create_table(
        "carts",
        sa.Column("id", sa.String(length=26), primary_key=True),
        sa.Column(
            "user_id",
            sa.String(length=26),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "status",
            postgresql.ENUM(
                "open", "converted", "abandoned", name="cart_status", create_type=False
            ),
            nullable=False,
            server_default="open",
        ),
        sa.Column(
            "coupon_id",
            sa.String(length=26),
            sa.ForeignKey("coupons.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_carts_user_id", "carts", ["user_id"])
    op.create_index("ix_carts_coupon_id", "carts", ["coupon_id"])
    # Partial unique index: at most one open cart per user.
    op.create_index(
        "uq_carts_user_open",
        "carts",
        ["user_id"],
        unique=True,
        postgresql_where=sa.text("status = 'open'"),
    )

    # --- cart_items -------------------------------------------------------
    op.create_table(
        "cart_items",
        sa.Column("id", sa.String(length=26), primary_key=True),
        sa.Column(
            "cart_id",
            sa.String(length=26),
            sa.ForeignKey("carts.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "product_id",
            sa.String(length=26),
            sa.ForeignKey("products.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("unit_price_cents", sa.Integer(), nullable=False),
        sa.Column(
            "modifiers_total_cents",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
        sa.Column(
            "customizations",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "added_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint("quantity BETWEEN 1 AND 20", name="ck_cart_items_quantity_range"),
        sa.CheckConstraint("unit_price_cents >= 0", name="ck_cart_items_unit_price_non_negative"),
    )
    op.create_index("ix_cart_items_cart_id", "cart_items", ["cart_id"])
    op.create_index("ix_cart_items_product_id", "cart_items", ["product_id"])


def downgrade() -> None:
    op.drop_index("ix_cart_items_product_id", table_name="cart_items")
    op.drop_index("ix_cart_items_cart_id", table_name="cart_items")
    op.drop_table("cart_items")

    op.drop_index("uq_carts_user_open", table_name="carts")
    op.drop_index("ix_carts_coupon_id", table_name="carts")
    op.drop_index("ix_carts_user_id", table_name="carts")
    op.drop_table("carts")

    op.drop_table("coupons")

    bind = op.get_bind()
    for enum_name in ("coupon_status", "cart_status"):
        postgresql.ENUM(name=enum_name).drop(bind, checkfirst=True)
