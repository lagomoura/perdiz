"""Admin category repository — sees drafts/archived, can mutate."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.category import Category


async def list_all(
    db: AsyncSession, *, status: str | None = None, include_deleted: bool = False
) -> list[Category]:
    stmt = select(Category)
    if not include_deleted:
        stmt = stmt.where(Category.deleted_at.is_(None))
    if status:
        stmt = stmt.where(Category.status == status)
    stmt = stmt.order_by(Category.sort_order.asc(), Category.name.asc())
    rows = await db.execute(stmt)
    return list(rows.scalars().all())


async def get_by_id(db: AsyncSession, category_id: str) -> Category | None:
    cat = await db.get(Category, category_id)
    if cat is None or cat.deleted_at is not None:
        return None
    return cat


async def create(
    db: AsyncSession,
    *,
    name: str,
    slug: str,
    parent_id: str | None,
    description: str | None,
    image_url: str | None,
    sort_order: int,
    status: str,
) -> Category:
    cat = Category(
        name=name,
        slug=slug,
        parent_id=parent_id,
        description=description,
        image_url=image_url,
        sort_order=sort_order,
        status=status,
    )
    db.add(cat)
    await db.flush()
    await db.refresh(cat)
    return cat


def apply_updates(cat: Category, updates: dict) -> None:  # type: ignore[type-arg]
    for key, value in updates.items():
        setattr(cat, key, value)


async def soft_delete(db: AsyncSession, cat: Category) -> None:
    cat.deleted_at = datetime.now(tz=UTC)
    cat.status = "archived"
    await db.flush()
