"""Admin router aggregator. Every sub-router here already applies
``require_role('admin')`` (non-admins get 404 to avoid enumeration).
"""

from __future__ import annotations

from fastapi import APIRouter

from app.api.v1.admin import categories, products

admin_router = APIRouter()
admin_router.include_router(categories.router)
admin_router.include_router(products.router)
