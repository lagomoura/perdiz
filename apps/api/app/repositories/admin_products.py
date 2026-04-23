"""Admin product repository — sees drafts/archived, can mutate."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.product import Product


async def list_all(
    db: AsyncSession,
    *,
    status: str | None = None,
    category_id: str | None = None,
    include_deleted: bool = False,
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[Product], int]:
    base = select(Product)
    if not include_deleted:
        base = base.where(Product.deleted_at.is_(None))
    if status:
        base = base.where(Product.status == status)
    if category_id:
        base = base.where(Product.category_id == category_id)

    count_stmt = select(func.count()).select_from(base.subquery())
    count = (await db.execute(count_stmt)).scalar_one()

    stmt = base.order_by(Product.id.desc()).limit(limit).offset(offset)
    rows = await db.execute(stmt)
    return list(rows.scalars().all()), int(count)


async def get_by_id(db: AsyncSession, product_id: str) -> Product | None:
    product = await db.get(Product, product_id)
    if product is None or product.deleted_at is not None:
        return None
    return product


async def create(db: AsyncSession, **fields) -> Product:  # type: ignore[no-untyped-def]
    product = Product(**fields)
    db.add(product)
    await db.flush()
    await db.refresh(product)
    return product


def apply_updates(product: Product, updates: dict) -> None:  # type: ignore[type-arg]
    for key, value in updates.items():
        setattr(product, key, value)


async def soft_delete(db: AsyncSession, product: Product) -> None:
    product.deleted_at = datetime.now(tz=UTC)
    if product.status != "archived":
        product.status = "archived"
    await db.flush()
