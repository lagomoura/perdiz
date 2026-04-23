"""Admin category endpoints. Require role='admin'; non-admins see 404."""

from __future__ import annotations

from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query

from app.api.deps import DbSession, require_role
from app.models.user import User
from app.schemas.admin_catalog import (
    CategoryAdmin,
    CategoryAdminListOut,
    CategoryAdminOut,
    CategoryCreateIn,
    CategoryUpdateIn,
)
from app.services.catalog import admin as admin_service

router = APIRouter(
    prefix="/admin/categories",
    tags=["admin-catalog"],
    dependencies=[Depends(require_role("admin"))],
)


def _serialize(cat) -> CategoryAdmin:  # type: ignore[no-untyped-def]
    return CategoryAdmin(
        id=cat.id,
        name=cat.name,
        slug=cat.slug,
        parent_id=cat.parent_id,
        description=cat.description,
        image_url=cat.image_url,
        sort_order=cat.sort_order,
        status=cat.status,
        created_at=cat.created_at,
        updated_at=cat.updated_at,
        deleted_at=cat.deleted_at,
    )


@router.get("", response_model=CategoryAdminListOut)
async def list_categories(
    db: DbSession,
    status: Annotated[Literal["active", "archived"] | None, Query()] = None,
) -> CategoryAdminListOut:
    cats = await admin_service.list_categories(db, status=status)
    return CategoryAdminListOut(data=[_serialize(c) for c in cats])


@router.post("", response_model=CategoryAdminOut, status_code=201)
async def create_category(
    payload: CategoryCreateIn,
    db: DbSession,
    actor: Annotated[User, Depends(require_role("admin"))],
) -> CategoryAdminOut:
    cat = await admin_service.create_category(
        db,
        actor=actor,
        name=payload.name,
        slug=payload.slug,
        parent_id=payload.parent_id,
        description=payload.description,
        image_url=payload.image_url,
        sort_order=payload.sort_order,
        status=payload.status,
    )
    return CategoryAdminOut(category=_serialize(cat))


@router.get("/{category_id}", response_model=CategoryAdminOut)
async def get_category(category_id: str, db: DbSession) -> CategoryAdminOut:
    cat = await admin_service.get_category(db, category_id)
    return CategoryAdminOut(category=_serialize(cat))


@router.patch("/{category_id}", response_model=CategoryAdminOut)
async def update_category(
    category_id: str,
    payload: CategoryUpdateIn,
    db: DbSession,
    actor: Annotated[User, Depends(require_role("admin"))],
) -> CategoryAdminOut:
    updates = payload.model_dump(exclude_unset=True)
    cat = await admin_service.update_category(
        db, actor=actor, category_id=category_id, updates=updates
    )
    return CategoryAdminOut(category=_serialize(cat))


@router.delete("/{category_id}", status_code=204)
async def delete_category(
    category_id: str,
    db: DbSession,
    actor: Annotated[User, Depends(require_role("admin"))],
) -> None:
    await admin_service.delete_category(db, actor=actor, category_id=category_id)
