"""Admin product_images endpoints (metadata; real uploads in PR #7)."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Response

from app.api.deps import DbSession, require_role
from app.models.user import User
from app.schemas.admin_customization import (
    ProductImageAdmin,
    ProductImageCreateIn,
    ProductImageListOut,
    ProductImageOut,
    ProductImageUpdateIn,
)
from app.services.catalog import admin_product_images as service

router = APIRouter(
    prefix="/admin/products/{product_id}/images",
    tags=["admin-catalog"],
    dependencies=[Depends(require_role("admin"))],
)


def _to_dto(image, media) -> ProductImageAdmin:  # type: ignore[no-untyped-def]
    return ProductImageAdmin(
        id=image.id,
        product_id=image.product_id,
        media_file_id=image.media_file_id,
        alt_text=image.alt_text,
        sort_order=image.sort_order,
        url=service.resolve_url(media),
    )


@router.get("", response_model=ProductImageListOut)
async def list_images(product_id: str, db: DbSession) -> ProductImageListOut:
    rows = await service.list_images(db, product_id)
    return ProductImageListOut(data=[_to_dto(pi, mf) for pi, mf in rows])


@router.post("", response_model=ProductImageOut, status_code=201)
async def create_image(
    product_id: str,
    payload: ProductImageCreateIn,
    db: DbSession,
    actor: Annotated[User, Depends(require_role("admin"))],
) -> ProductImageOut:
    image, media = await service.create_image(
        db,
        actor=actor,
        product_id=product_id,
        media_file_id=payload.media_file_id,
        alt_text=payload.alt_text,
        sort_order=payload.sort_order,
    )
    return ProductImageOut(image=_to_dto(image, media))


@router.patch("/{image_id}", response_model=ProductImageOut)
async def update_image(
    product_id: str,
    image_id: str,
    payload: ProductImageUpdateIn,
    db: DbSession,
    actor: Annotated[User, Depends(require_role("admin"))],
) -> ProductImageOut:
    updates = payload.model_dump(exclude_unset=True)
    image, media = await service.update_image(
        db, actor=actor, product_id=product_id, image_id=image_id, updates=updates
    )
    return ProductImageOut(image=_to_dto(image, media))


@router.delete("/{image_id}", status_code=204)
async def delete_image(
    product_id: str,
    image_id: str,
    db: DbSession,
    actor: Annotated[User, Depends(require_role("admin"))],
) -> Response:
    await service.delete_image(db, actor=actor, product_id=product_id, image_id=image_id)
    return Response(status_code=204)
