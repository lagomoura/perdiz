"""Media file model. Covers images, STL, GLB and user uploads.

Files live in R2 (or MinIO locally); the DB only stores metadata and the
object storage key.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import BigInteger, DateTime, Enum, ForeignKey, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, ULIDMixin

media_kind_enum = Enum(
    "image",
    "model_stl",
    "model_glb",
    "user_upload_image",
    "user_upload_model",
    name="media_kind",
    create_type=True,
)


class MediaFile(Base, ULIDMixin):
    __tablename__ = "media_files"
    __table_args__ = (UniqueConstraint("storage_key", name="uq_media_files_storage_key"),)

    owner_user_id: Mapped[str | None] = mapped_column(
        String(26), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    kind: Mapped[str] = mapped_column(media_kind_enum, nullable=False)
    mime_type: Mapped[str] = mapped_column(Text, nullable=False)
    size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    storage_key: Mapped[str] = mapped_column(Text, nullable=False)
    public_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    checksum_sha256: Mapped[str | None] = mapped_column(Text, nullable=True)
    # SQLAlchemy reserves the attribute name ``metadata`` on declarative bases;
    # the column is still called ``metadata`` in Postgres.
    file_metadata: Mapped[dict[str, Any]] = mapped_column(
        "metadata", JSONB, nullable=False, server_default="{}"
    )
    # Self-FK so a derived file (e.g. Draco-compressed GLB) points to its
    # source STL. ON DELETE SET NULL to preserve the derived file if the
    # source is removed.
    derived_from_id: Mapped[str | None] = mapped_column(
        String(26), ForeignKey("media_files.id", ondelete="SET NULL"), nullable=True, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
