"""Aggregate model imports so Alembic sees everything in Base.metadata.

Add new model modules here as they are created.
"""

from __future__ import annotations

from app.models.email_verification_token import EmailVerificationToken
from app.models.refresh_token import RefreshToken
from app.models.user import User

__all__ = ["EmailVerificationToken", "RefreshToken", "User"]
