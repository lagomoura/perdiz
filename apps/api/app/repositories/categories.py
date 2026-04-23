"""Category repository."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.category import Category


async def list_active(db: AsyncSession) -> list[Category]:
    result = await db.execute(
        select(Category)
        .where(Category.status == "active", Category.deleted_at.is_(None))
        .order_by(Category.sort_order.asc(), Category.name.asc())
    )
    return list(result.scalars().all())


async def get_active_by_slug(db: AsyncSession, slug: str) -> Category | None:
    result = await db.execute(
        select(Category).where(
            Category.slug == slug,
            Category.status == "active",
            Category.deleted_at.is_(None),
        )
    )
    return result.scalar_one_or_none()
