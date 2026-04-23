"""v1 API router aggregator."""

from __future__ import annotations

from fastapi import APIRouter

from app.api.v1 import auth, categories, health, products, uploads, users
from app.api.v1.admin import admin_router

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(categories.router)
api_router.include_router(products.router)
api_router.include_router(uploads.router)
api_router.include_router(admin_router)
