"""Admin repository for product_images (metadata only; uploads in PR #7)."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.media_file import MediaFile
from app.models.product_image import ProductImage


async def list_for_product(
    db: AsyncSession, product_id: str
) -> list[tuple[ProductImage, MediaFile]]:
    rows = await db.execute(
        select(ProductImage, MediaFile)
        .join(MediaFile, ProductImage.media_file_id == MediaFile.id)
        .where(ProductImage.product_id == product_id)
        .order_by(ProductImage.sort_order.asc())
    )
    return [(pi, mf) for pi, mf in rows.all()]


async def get(db: AsyncSession, image_id: str) -> ProductImage | None:
    return await db.get(ProductImage, image_id)


async def create(
    db: AsyncSession,
    *,
    product_id: str,
    media_file_id: str,
    alt_text: str | None,
    sort_order: int,
) -> ProductImage:
    image = ProductImage(
        product_id=product_id,
        media_file_id=media_file_id,
        alt_text=alt_text,
        sort_order=sort_order,
    )
    db.add(image)
    await db.flush()
    await db.refresh(image)
    return image


def apply_updates(image: ProductImage, updates: dict) -> None:  # type: ignore[type-arg]
    for key, value in updates.items():
        setattr(image, key, value)


async def delete(db: AsyncSession, image: ProductImage) -> None:
    await db.delete(image)
    await db.flush()
