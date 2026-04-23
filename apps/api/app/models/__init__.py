"""Aggregate model imports so Alembic sees everything in Base.metadata.

Add new model modules here as they are created. Python import order is
irrelevant (SQLAlchemy resolves FKs via string references at class
definition time); imports are kept alphabetical for readability.
"""

from __future__ import annotations

from app.models.audit_log import AuditLog
from app.models.automatic_discount import AutomaticDiscount
from app.models.category import Category
from app.models.customization_group import CustomizationGroup
from app.models.customization_option import CustomizationOption
from app.models.email_verification_token import EmailVerificationToken
from app.models.media_file import MediaFile
from app.models.product import Product
from app.models.product_image import ProductImage
from app.models.refresh_token import RefreshToken
from app.models.user import User
from app.models.volume_discount import VolumeDiscount

__all__ = [
    "AuditLog",
    "AutomaticDiscount",
    "Category",
    "CustomizationGroup",
    "CustomizationOption",
    "EmailVerificationToken",
    "MediaFile",
    "Product",
    "ProductImage",
    "RefreshToken",
    "User",
    "VolumeDiscount",
]
