"""Public category endpoints."""

from __future__ import annotations

from fastapi import APIRouter

from app.api.deps import DbSession
from app.schemas.catalog import (
    CategoryDetailOut,
    CategoryListOut,
    CategoryPublic,
)
from app.services.catalog import service as catalog_service

router = APIRouter(prefix="/categories", tags=["catalog"])


def _serialize(cat) -> CategoryPublic:  # type: ignore[no-untyped-def]
    return CategoryPublic(
        id=cat.id,
        name=cat.name,
        slug=cat.slug,
        description=cat.description,
        image_url=cat.image_url,
        sort_order=cat.sort_order,
    )


@router.get("", response_model=CategoryListOut)
async def list_categories(db: DbSession) -> CategoryListOut:
    cats = await catalog_service.list_categories(db)
    return CategoryListOut(data=[_serialize(c) for c in cats])


@router.get("/{slug}", response_model=CategoryDetailOut)
async def get_category(slug: str, db: DbSession) -> CategoryDetailOut:
    cat = await catalog_service.get_category(db, slug)
    return CategoryDetailOut(category=_serialize(cat))
