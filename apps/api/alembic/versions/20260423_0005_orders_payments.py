"""orders, order_items, order_status_history, payments, coupon_redemptions

Revision ID: 0005
Revises: 0004
Create Date: 2026-04-23

"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0005"
down_revision: str | Sequence[str] | None = "0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    postgresql.ENUM(
        "pending_payment",
        "paid",
        "queued",
        "printing",
        "shipped",
        "delivered",
        "cancelled",
        "refunded",
        name="order_status",
    ).create(bind, checkfirst=True)
    postgresql.ENUM("pickup", "standard", name="shipping_method").create(bind, checkfirst=True)
    postgresql.ENUM("mercadopago", "stripe", "paypal", name="payment_provider").create(
        bind, checkfirst=True
    )
    postgresql.ENUM("pending", "approved", "rejected", "refunded", name="payment_status").create(
        bind, checkfirst=True
    )

    op.create_table(
        "orders",
        sa.Column("id", sa.String(length=26), primary_key=True),
        sa.Column(
            "user_id",
            sa.String(length=26),
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "status",
            postgresql.ENUM(
                "pending_payment",
                "paid",
                "queued",
                "printing",
                "shipped",
                "delivered",
                "cancelled",
                "refunded",
                name="order_status",
                create_type=False,
            ),
            nullable=False,
            server_default="pending_payment",
        ),
        sa.Column("subtotal_cents", sa.Integer(), nullable=False),
        sa.Column("discount_cents", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("shipping_cents", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_cents", sa.Integer(), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False, server_default="ARS"),
        sa.Column(
            "coupon_id",
            sa.String(length=26),
            sa.ForeignKey("coupons.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("shipping_address_json", postgresql.JSONB(), nullable=False),
        sa.Column(
            "shipping_method",
            postgresql.ENUM("pickup", "standard", name="shipping_method", create_type=False),
            nullable=False,
        ),
        sa.Column("admin_notes", sa.Text(), nullable=True),
        sa.Column(
            "placed_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("paid_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("shipped_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("delivered_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("refunded_at", sa.DateTime(timezone=True), nullable=True),
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
        sa.CheckConstraint("subtotal_cents >= 0", name="ck_orders_subtotal_non_negative"),
        sa.CheckConstraint("discount_cents >= 0", name="ck_orders_discount_non_negative"),
        sa.CheckConstraint("shipping_cents >= 0", name="ck_orders_shipping_non_negative"),
        sa.CheckConstraint("total_cents >= 0", name="ck_orders_total_non_negative"),
    )
    op.create_index("ix_orders_user_id", "orders", ["user_id"])
    op.create_index("ix_orders_status", "orders", ["status"])
    op.create_index("ix_orders_placed_at", "orders", ["placed_at"])

    op.create_table(
        "order_items",
        sa.Column("id", sa.String(length=26), primary_key=True),
        sa.Column(
            "order_id",
            sa.String(length=26),
            sa.ForeignKey("orders.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "product_id",
            sa.String(length=26),
            sa.ForeignKey("products.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("product_name_snapshot", sa.Text(), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("unit_price_cents", sa.Integer(), nullable=False),
        sa.Column(
            "modifiers_total_cents",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
        sa.Column("line_total_cents", sa.Integer(), nullable=False),
        sa.Column(
            "customizations",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.CheckConstraint("quantity > 0", name="ck_order_items_quantity_positive"),
        sa.CheckConstraint("unit_price_cents >= 0", name="ck_order_items_unit_price_non_negative"),
        sa.CheckConstraint(
            "line_total_cents >= 0",
            name="ck_order_items_line_total_non_negative",
        ),
    )
    op.create_index("ix_order_items_order_id", "order_items", ["order_id"])

    op.create_table(
        "order_status_history",
        sa.Column("id", sa.String(length=26), primary_key=True),
        sa.Column(
            "order_id",
            sa.String(length=26),
            sa.ForeignKey("orders.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "from_status",
            postgresql.ENUM(
                "pending_payment",
                "paid",
                "queued",
                "printing",
                "shipped",
                "delivered",
                "cancelled",
                "refunded",
                name="order_status",
                create_type=False,
            ),
            nullable=True,
        ),
        sa.Column(
            "to_status",
            postgresql.ENUM(
                "pending_payment",
                "paid",
                "queued",
                "printing",
                "shipped",
                "delivered",
                "cancelled",
                "refunded",
                name="order_status",
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column(
            "changed_by",
            sa.String(length=26),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column(
            "changed_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_order_status_history_order_id", "order_status_history", ["order_id"])

    op.create_table(
        "payments",
        sa.Column("id", sa.String(length=26), primary_key=True),
        sa.Column(
            "order_id",
            sa.String(length=26),
            sa.ForeignKey("orders.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "provider",
            postgresql.ENUM(
                "mercadopago",
                "stripe",
                "paypal",
                name="payment_provider",
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column("provider_payment_id", sa.Text(), nullable=False),
        sa.Column(
            "status",
            postgresql.ENUM(
                "pending",
                "approved",
                "rejected",
                "refunded",
                name="payment_status",
                create_type=False,
            ),
            nullable=False,
            server_default="pending",
        ),
        sa.Column("amount_cents", sa.Integer(), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False, server_default="ARS"),
        sa.Column(
            "raw_webhook_events",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
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
        sa.UniqueConstraint("provider", "provider_payment_id", name="uq_payments_provider_ref"),
    )
    op.create_index("ix_payments_order_id", "payments", ["order_id"])

    op.create_table(
        "coupon_redemptions",
        sa.Column("id", sa.String(length=26), primary_key=True),
        sa.Column(
            "coupon_id",
            sa.String(length=26),
            sa.ForeignKey("coupons.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "order_id",
            sa.String(length=26),
            sa.ForeignKey("orders.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            sa.String(length=26),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "redeemed_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_coupon_redemptions_coupon_id", "coupon_redemptions", ["coupon_id"])
    op.create_index("ix_coupon_redemptions_order_id", "coupon_redemptions", ["order_id"])
    op.create_index("ix_coupon_redemptions_user_id", "coupon_redemptions", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_coupon_redemptions_user_id", table_name="coupon_redemptions")
    op.drop_index("ix_coupon_redemptions_order_id", table_name="coupon_redemptions")
    op.drop_index("ix_coupon_redemptions_coupon_id", table_name="coupon_redemptions")
    op.drop_table("coupon_redemptions")
    op.drop_index("ix_payments_order_id", table_name="payments")
    op.drop_table("payments")
    op.drop_index("ix_order_status_history_order_id", table_name="order_status_history")
    op.drop_table("order_status_history")
    op.drop_index("ix_order_items_order_id", table_name="order_items")
    op.drop_table("order_items")
    op.drop_index("ix_orders_placed_at", table_name="orders")
    op.drop_index("ix_orders_status", table_name="orders")
    op.drop_index("ix_orders_user_id", table_name="orders")
    op.drop_table("orders")
    bind = op.get_bind()
    for enum_name in (
        "payment_status",
        "payment_provider",
        "shipping_method",
        "order_status",
    ):
        postgresql.ENUM(name=enum_name).drop(bind, checkfirst=True)
