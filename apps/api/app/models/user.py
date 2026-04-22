"""User model."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Enum, Text
from sqlalchemy.dialects.postgresql import CITEXT
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, SoftDeleteMixin, TimestampMixin, ULIDMixin

user_role_enum = Enum("user", "admin", name="user_role", create_type=True)
user_status_enum = Enum("active", "suspended", name="user_status", create_type=True)


class User(Base, ULIDMixin, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "users"

    email: Mapped[str] = mapped_column(CITEXT, unique=True, nullable=False)
    email_verified_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    password_hash: Mapped[str | None] = mapped_column(Text, nullable=True)
    role: Mapped[str] = mapped_column(user_role_enum, nullable=False, default="user")
    status: Mapped[str] = mapped_column(user_status_enum, nullable=False, default="active")
    first_name: Mapped[str | None] = mapped_column(Text, nullable=True)
    last_name: Mapped[str | None] = mapped_column(Text, nullable=True)
    phone: Mapped[str | None] = mapped_column(Text, nullable=True)
    dni: Mapped[str | None] = mapped_column(Text, nullable=True)

    @property
    def is_verified(self) -> bool:
        return self.email_verified_at is not None
