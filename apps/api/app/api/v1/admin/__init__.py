"""Admin router aggregator. Every sub-router here already applies
``require_role('admin')`` (non-admins get 404 to avoid enumeration).
"""

from __future__ import annotations

from fastapi import APIRouter

from app.api.v1.admin import (
    categories,
    coupons,
    customization,
    discounts,
    product_images,
    products,
    uploads,
)

admin_router = APIRouter()
admin_router.include_router(categories.router)
admin_router.include_router(products.router)
admin_router.include_router(customization.router)
admin_router.include_router(product_images.router)
admin_router.include_router(discounts.router)
admin_router.include_router(uploads.router)
admin_router.include_router(coupons.router)
