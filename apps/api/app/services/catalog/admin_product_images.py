"""Admin service for product_images (metadata; uploads in PR #7)."""

from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.exceptions import NotFoundError, ValidationError
from app.models.media_file import MediaFile
from app.models.product_image import ProductImage
from app.models.user import User
from app.repositories import admin_product_images as repo
from app.repositories import admin_products as prod_repo
from app.services import audit


def _resolve_url(media: MediaFile) -> str | None:
    if media.public_url:
        return media.public_url
    if settings.r2_public_base_url:
        return f"{settings.r2_public_base_url.rstrip('/')}/{media.storage_key}"
    return None


async def list_images(db: AsyncSession, product_id: str) -> list[tuple[ProductImage, MediaFile]]:
    if await prod_repo.get_by_id(db, product_id) is None:
        raise NotFoundError("Producto no encontrado.")
    return await repo.list_for_product(db, product_id)


async def create_image(
    db: AsyncSession,
    *,
    actor: User,
    product_id: str,
    media_file_id: str,
    alt_text: str | None,
    sort_order: int,
) -> tuple[ProductImage, MediaFile]:
    if await prod_repo.get_by_id(db, product_id) is None:
        raise NotFoundError("Producto no encontrado.")
    media = await db.get(MediaFile, media_file_id)
    if media is None or media.deleted_at is not None:
        raise ValidationError("El archivo de media no existe.", details={"field": "media_file_id"})
    if media.kind != "image":
        raise ValidationError(
            "El media_file referenciado no es una imagen.",
            details={"field": "media_file_id"},
        )
    image = await repo.create(
        db,
        product_id=product_id,
        media_file_id=media_file_id,
        alt_text=alt_text,
        sort_order=sort_order,
    )
    await audit.log_mutation(
        db,
        actor=actor,
        action="product_image.create",
        entity_type="product_image",
        entity_id=image.id,
        before=None,
        after=audit.snapshot(image),
    )
    await db.commit()
    return image, media


async def update_image(
    db: AsyncSession,
    *,
    actor: User,
    product_id: str,
    image_id: str,
    updates: dict[str, Any],
) -> tuple[ProductImage, MediaFile]:
    image = await repo.get(db, image_id)
    if image is None or image.product_id != product_id:
        raise NotFoundError("Imagen no encontrada.")
    before = audit.snapshot(image)
    repo.apply_updates(image, updates)
    await db.flush()
    await db.refresh(image)
    media = await db.get(MediaFile, image.media_file_id)
    assert media is not None
    await audit.log_mutation(
        db,
        actor=actor,
        action="product_image.update",
        entity_type="product_image",
        entity_id=image.id,
        before=before,
        after=audit.snapshot(image),
    )
    await db.commit()
    return image, media


async def delete_image(db: AsyncSession, *, actor: User, product_id: str, image_id: str) -> None:
    image = await repo.get(db, image_id)
    if image is None or image.product_id != product_id:
        raise NotFoundError("Imagen no encontrada.")
    before = audit.snapshot(image)
    await repo.delete(db, image)
    await audit.log_mutation(
        db,
        actor=actor,
        action="product_image.delete",
        entity_type="product_image",
        entity_id=image_id,
        before=before,
        after=None,
    )
    await db.commit()


resolve_url = _resolve_url
