"""catalog schema: categories, media_files, products, product_images,
customization_groups, customization_options, volume_discounts, automatic_discounts

Revision ID: 0002
Revises: 0001
Create Date: 2026-04-22

"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0002"
down_revision: str | Sequence[str] | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


# Name + description only. ``tags`` lives in its own GIN index
# (``ix_products_tags``) because array_to_string over polymorphic arrays is
# not considered immutable by Postgres and can't be used in STORED
# generated columns. Tag search uses ``tags @> ARRAY[...]`` at query time.
_SEARCH_TSV_EXPRESSION = (
    "setweight(to_tsvector('spanish'::regconfig, coalesce(name, '')), 'A') || "
    "setweight(to_tsvector('spanish'::regconfig, coalesce(description, '')), 'B')"
)


def _enum(*values: str, name: str) -> postgresql.ENUM:
    return postgresql.ENUM(*values, name=name, create_type=False)


def upgrade() -> None:
    bind = op.get_bind()

    # --- Enums ------------------------------------------------------------
    postgresql.ENUM("active", "archived", name="category_status").create(bind, checkfirst=True)
    postgresql.ENUM(
        "image",
        "model_stl",
        "model_glb",
        "user_upload_image",
        "user_upload_model",
        name="media_kind",
    ).create(bind, checkfirst=True)
    postgresql.ENUM("stocked", "print_on_demand", name="stock_mode").create(bind, checkfirst=True)
    postgresql.ENUM("draft", "active", "archived", name="product_status").create(
        bind, checkfirst=True
    )
    postgresql.ENUM(
        "COLOR",
        "MATERIAL",
        "SIZE",
        "ENGRAVING_TEXT",
        "ENGRAVING_IMAGE",
        "USER_FILE",
        name="customization_type",
    ).create(bind, checkfirst=True)
    postgresql.ENUM("single", "multiple", name="customization_selection").create(
        bind, checkfirst=True
    )
    postgresql.ENUM("percentage", "fixed", name="discount_type").create(bind, checkfirst=True)
    postgresql.ENUM("category", "product", name="discount_scope").create(bind, checkfirst=True)
    postgresql.ENUM("active", "disabled", name="discount_status").create(bind, checkfirst=True)

    # --- categories -------------------------------------------------------
    op.create_table(
        "categories",
        sa.Column("id", sa.String(length=26), primary_key=True),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("slug", sa.Text(), nullable=False),
        sa.Column(
            "parent_id",
            sa.String(length=26),
            sa.ForeignKey("categories.id", ondelete="RESTRICT"),
            nullable=True,
        ),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("image_url", sa.Text(), nullable=True),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "status",
            _enum("active", "archived", name="category_status"),
            nullable=False,
            server_default="active",
        ),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("slug", name="uq_categories_slug"),
    )
    op.create_index("ix_categories_parent_id", "categories", ["parent_id"])

    # --- media_files ------------------------------------------------------
    op.create_table(
        "media_files",
        sa.Column("id", sa.String(length=26), primary_key=True),
        sa.Column(
            "owner_user_id",
            sa.String(length=26),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "kind",
            _enum(
                "image",
                "model_stl",
                "model_glb",
                "user_upload_image",
                "user_upload_model",
                name="media_kind",
            ),
            nullable=False,
        ),
        sa.Column("mime_type", sa.Text(), nullable=False),
        sa.Column("size_bytes", sa.BigInteger(), nullable=False),
        sa.Column("storage_key", sa.Text(), nullable=False),
        sa.Column("public_url", sa.Text(), nullable=True),
        sa.Column("checksum_sha256", sa.Text(), nullable=True),
        sa.Column(
            "metadata", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")
        ),
        sa.Column(
            "derived_from_id",
            sa.String(length=26),
            sa.ForeignKey("media_files.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("storage_key", name="uq_media_files_storage_key"),
    )
    op.create_index("ix_media_files_owner_user_id", "media_files", ["owner_user_id"])
    op.create_index("ix_media_files_derived_from_id", "media_files", ["derived_from_id"])

    # --- products ---------------------------------------------------------
    op.create_table(
        "products",
        sa.Column("id", sa.String(length=26), primary_key=True),
        sa.Column(
            "category_id",
            sa.String(length=26),
            sa.ForeignKey("categories.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("slug", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("base_price_cents", sa.Integer(), nullable=False),
        sa.Column(
            "stock_mode",
            _enum("stocked", "print_on_demand", name="stock_mode"),
            nullable=False,
        ),
        sa.Column("stock_quantity", sa.Integer(), nullable=True),
        sa.Column("lead_time_days", sa.Integer(), nullable=True),
        sa.Column("weight_grams", sa.Integer(), nullable=True),
        sa.Column("dimensions_mm", postgresql.ARRAY(sa.Integer()), nullable=True),
        sa.Column("sku", sa.Text(), nullable=False),
        sa.Column(
            "tags",
            postgresql.ARRAY(sa.Text()),
            nullable=False,
            server_default=sa.text("ARRAY[]::text[]"),
        ),
        sa.Column(
            "status",
            _enum("draft", "active", "archived", name="product_status"),
            nullable=False,
            server_default="draft",
        ),
        sa.Column(
            "search_tsv",
            postgresql.TSVECTOR(),
            sa.Computed(_SEARCH_TSV_EXPRESSION, persisted=True),
            nullable=True,
        ),
        sa.Column(
            "model_file_id",
            sa.String(length=26),
            sa.ForeignKey("media_files.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("slug", name="uq_products_slug"),
        sa.UniqueConstraint("sku", name="uq_products_sku"),
        sa.CheckConstraint("base_price_cents >= 0", name="ck_products_base_price_non_negative"),
        sa.CheckConstraint(
            "stock_quantity IS NULL OR stock_quantity >= 0",
            name="ck_products_stock_quantity_non_negative",
        ),
        sa.CheckConstraint(
            "lead_time_days IS NULL OR lead_time_days >= 1",
            name="ck_products_lead_time_positive",
        ),
        sa.CheckConstraint(
            "(stock_mode = 'stocked' AND stock_quantity IS NOT NULL "
            "AND lead_time_days IS NULL) "
            "OR (stock_mode = 'print_on_demand' AND lead_time_days IS NOT NULL "
            "AND stock_quantity IS NULL)",
            name="ck_products_stock_mode_consistency",
        ),
    )
    op.create_index("ix_products_category_id", "products", ["category_id"])
    op.create_index("ix_products_category_id_status", "products", ["category_id", "status"])
    op.create_index(
        "ix_products_tags",
        "products",
        ["tags"],
        postgresql_using="gin",
    )
    op.create_index(
        "ix_products_search_tsv",
        "products",
        ["search_tsv"],
        postgresql_using="gin",
    )

    # --- product_images ---------------------------------------------------
    op.create_table(
        "product_images",
        sa.Column("id", sa.String(length=26), primary_key=True),
        sa.Column(
            "product_id",
            sa.String(length=26),
            sa.ForeignKey("products.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "media_file_id",
            sa.String(length=26),
            sa.ForeignKey("media_files.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("alt_text", sa.Text(), nullable=True),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
    )
    op.create_index("ix_product_images_product_id", "product_images", ["product_id"])

    # --- customization_groups ---------------------------------------------
    op.create_table(
        "customization_groups",
        sa.Column("id", sa.String(length=26), primary_key=True),
        sa.Column(
            "product_id",
            sa.String(length=26),
            sa.ForeignKey("products.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column(
            "type",
            _enum(
                "COLOR",
                "MATERIAL",
                "SIZE",
                "ENGRAVING_TEXT",
                "ENGRAVING_IMAGE",
                "USER_FILE",
                name="customization_type",
            ),
            nullable=False,
        ),
        sa.Column("required", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column(
            "selection_mode",
            _enum("single", "multiple", name="customization_selection"),
            nullable=False,
        ),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "metadata", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")
        ),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_index("ix_customization_groups_product_id", "customization_groups", ["product_id"])

    # --- customization_options --------------------------------------------
    op.create_table(
        "customization_options",
        sa.Column("id", sa.String(length=26), primary_key=True),
        sa.Column(
            "group_id",
            sa.String(length=26),
            sa.ForeignKey("customization_groups.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("label", sa.Text(), nullable=False),
        sa.Column("price_modifier_cents", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_default", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("is_available", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "metadata", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")
        ),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_index("ix_customization_options_group_id", "customization_options", ["group_id"])

    # --- volume_discounts -------------------------------------------------
    op.create_table(
        "volume_discounts",
        sa.Column("id", sa.String(length=26), primary_key=True),
        sa.Column(
            "product_id",
            sa.String(length=26),
            sa.ForeignKey("products.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("min_quantity", sa.Integer(), nullable=False),
        sa.Column(
            "type",
            _enum("percentage", "fixed", name="discount_type"),
            nullable=False,
        ),
        sa.Column("value", sa.Integer(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint("min_quantity >= 2", name="ck_volume_discounts_min_quantity"),
        sa.CheckConstraint("value > 0", name="ck_volume_discounts_value_positive"),
    )
    op.create_index("ix_volume_discounts_product_id", "volume_discounts", ["product_id"])

    # --- automatic_discounts ----------------------------------------------
    op.create_table(
        "automatic_discounts",
        sa.Column("id", sa.String(length=26), primary_key=True),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column(
            "type",
            _enum("percentage", "fixed", name="discount_type"),
            nullable=False,
        ),
        sa.Column("value", sa.Integer(), nullable=False),
        sa.Column(
            "scope",
            _enum("category", "product", name="discount_scope"),
            nullable=False,
        ),
        sa.Column("target_id", sa.String(length=26), nullable=False),
        sa.Column("valid_from", sa.DateTime(timezone=True), nullable=True),
        sa.Column("valid_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "status",
            _enum("active", "disabled", name="discount_status"),
            nullable=False,
            server_default="active",
        ),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint("value > 0", name="ck_automatic_discounts_value_positive"),
    )
    op.create_index("ix_automatic_discounts_target_id", "automatic_discounts", ["target_id"])


def downgrade() -> None:
    op.drop_index("ix_automatic_discounts_target_id", table_name="automatic_discounts")
    op.drop_table("automatic_discounts")

    op.drop_index("ix_volume_discounts_product_id", table_name="volume_discounts")
    op.drop_table("volume_discounts")

    op.drop_index("ix_customization_options_group_id", table_name="customization_options")
    op.drop_table("customization_options")

    op.drop_index("ix_customization_groups_product_id", table_name="customization_groups")
    op.drop_table("customization_groups")

    op.drop_index("ix_product_images_product_id", table_name="product_images")
    op.drop_table("product_images")

    op.drop_index("ix_products_search_tsv", table_name="products")
    op.drop_index("ix_products_tags", table_name="products")
    op.drop_index("ix_products_category_id_status", table_name="products")
    op.drop_index("ix_products_category_id", table_name="products")
    op.drop_table("products")

    op.drop_index("ix_media_files_derived_from_id", table_name="media_files")
    op.drop_index("ix_media_files_owner_user_id", table_name="media_files")
    op.drop_table("media_files")

    op.drop_index("ix_categories_parent_id", table_name="categories")
    op.drop_table("categories")

    bind = op.get_bind()
    for enum_name in (
        "discount_status",
        "discount_scope",
        "discount_type",
        "customization_selection",
        "customization_type",
        "product_status",
        "stock_mode",
        "media_kind",
        "category_status",
    ):
        postgresql.ENUM(name=enum_name).drop(bind, checkfirst=True)
