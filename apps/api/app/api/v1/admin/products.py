"""Admin product endpoints."""

from __future__ import annotations

from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query, Response

from app.api.deps import DbSession, require_role
from app.models.user import User
from app.schemas.admin_catalog import (
    ProductAdmin,
    ProductAdminListOut,
    ProductAdminOut,
    ProductCreateIn,
    ProductStatusTransitionIn,
    ProductUpdateIn,
)
from app.services.catalog import admin as admin_service

router = APIRouter(
    prefix="/admin/products",
    tags=["admin-catalog"],
    dependencies=[Depends(require_role("admin"))],
)


def _serialize(p) -> ProductAdmin:  # type: ignore[no-untyped-def]
    return ProductAdmin(
        id=p.id,
        category_id=p.category_id,
        name=p.name,
        slug=p.slug,
        description=p.description,
        base_price_cents=p.base_price_cents,
        stock_mode=p.stock_mode,
        stock_quantity=p.stock_quantity,
        lead_time_days=p.lead_time_days,
        weight_grams=p.weight_grams,
        dimensions_mm=list(p.dimensions_mm) if p.dimensions_mm else None,
        sku=p.sku,
        tags=list(p.tags or []),
        status=p.status,
        model_file_id=p.model_file_id,
        created_at=p.created_at,
        updated_at=p.updated_at,
        deleted_at=p.deleted_at,
    )


@router.get("", response_model=ProductAdminListOut)
async def list_products(
    db: DbSession,
    status: Annotated[Literal["draft", "active", "archived"] | None, Query()] = None,
    category_id: Annotated[str | None, Query(max_length=26)] = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> ProductAdminListOut:
    products, count = await admin_service.list_products(
        db, status=status, category_id=category_id, limit=limit, offset=offset
    )
    return ProductAdminListOut(data=[_serialize(p) for p in products], count=count)


@router.post("", response_model=ProductAdminOut, status_code=201)
async def create_product(
    payload: ProductCreateIn,
    db: DbSession,
    actor: Annotated[User, Depends(require_role("admin"))],
) -> ProductAdminOut:
    product = await admin_service.create_product(db, actor=actor, payload=payload.model_dump())
    return ProductAdminOut(product=_serialize(product))


@router.get("/{product_id}", response_model=ProductAdminOut)
async def get_product(product_id: str, db: DbSession) -> ProductAdminOut:
    product = await admin_service.get_product(db, product_id)
    return ProductAdminOut(product=_serialize(product))


@router.patch("/{product_id}", response_model=ProductAdminOut)
async def update_product(
    product_id: str,
    payload: ProductUpdateIn,
    db: DbSession,
    actor: Annotated[User, Depends(require_role("admin"))],
) -> ProductAdminOut:
    updates = payload.model_dump(exclude_unset=True)
    product = await admin_service.update_product(
        db, actor=actor, product_id=product_id, updates=updates
    )
    return ProductAdminOut(product=_serialize(product))


@router.post("/{product_id}/transition-status", response_model=ProductAdminOut)
async def transition_status(
    product_id: str,
    payload: ProductStatusTransitionIn,
    db: DbSession,
    actor: Annotated[User, Depends(require_role("admin"))],
) -> ProductAdminOut:
    product = await admin_service.transition_product_status(
        db, actor=actor, product_id=product_id, to_status=payload.status
    )
    return ProductAdminOut(product=_serialize(product))


@router.delete("/{product_id}", status_code=204)
async def delete_product(
    product_id: str,
    db: DbSession,
    actor: Annotated[User, Depends(require_role("admin"))],
) -> Response:
    await admin_service.delete_product(db, actor=actor, product_id=product_id)
    return Response(status_code=204)
