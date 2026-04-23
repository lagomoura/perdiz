"""Product image join table ordering media files against a product."""

from __future__ import annotations

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, ULIDMixin


class ProductImage(Base, ULIDMixin):
    __tablename__ = "product_images"

    product_id: Mapped[str] = mapped_column(
        String(26), ForeignKey("products.id", ondelete="CASCADE"), nullable=False, index=True
    )
    media_file_id: Mapped[str] = mapped_column(
        String(26), ForeignKey("media_files.id", ondelete="RESTRICT"), nullable=False
    )
    alt_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
