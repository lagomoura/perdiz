"""audit_log table

Revision ID: 0003
Revises: 0002
Create Date: 2026-04-23

"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0003"
down_revision: str | Sequence[str] | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "audit_log",
        sa.Column("id", sa.String(length=26), primary_key=True),
        sa.Column(
            "actor_id",
            sa.String(length=26),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "actor_role",
            postgresql.ENUM("user", "admin", name="user_role", create_type=False),
            nullable=True,
        ),
        sa.Column("action", sa.Text(), nullable=False),
        sa.Column("entity_type", sa.Text(), nullable=False),
        sa.Column("entity_id", sa.String(length=26), nullable=True),
        sa.Column("before_json", postgresql.JSONB(), nullable=True),
        sa.Column("after_json", postgresql.JSONB(), nullable=True),
        sa.Column("ip", postgresql.INET(), nullable=True),
        sa.Column("user_agent", sa.Text(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_index("ix_audit_log_actor_id", "audit_log", ["actor_id"])
    op.create_index("ix_audit_log_entity_id", "audit_log", ["entity_id"])
    op.create_index(
        "ix_audit_log_entity_type_id_created",
        "audit_log",
        ["entity_type", "entity_id", "created_at"],
    )

    # Document-only: recommended DB-level hardening in production. The migration
    # doesn't run these because the roles aren't set up here; deployment scripts
    # should apply them. See docs/architecture/security.md § "Auditoría".
    #
    #   REVOKE UPDATE, DELETE ON audit_log FROM perdiz_app;
    #   GRANT INSERT, SELECT ON audit_log TO perdiz_app;


def downgrade() -> None:
    op.drop_index("ix_audit_log_entity_type_id_created", table_name="audit_log")
    op.drop_index("ix_audit_log_entity_id", table_name="audit_log")
    op.drop_index("ix_audit_log_actor_id", table_name="audit_log")
    op.drop_table("audit_log")
