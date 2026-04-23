"""Admin repositories for volume_discounts and automatic_discounts."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.automatic_discount import AutomaticDiscount
from app.models.volume_discount import VolumeDiscount

# --- Volume discounts --------------------------------------------------------


async def list_volume_for_product(db: AsyncSession, product_id: str) -> list[VolumeDiscount]:
    rows = await db.execute(
        select(VolumeDiscount)
        .where(VolumeDiscount.product_id == product_id)
        .order_by(VolumeDiscount.min_quantity.asc())
    )
    return list(rows.scalars().all())


async def get_volume(db: AsyncSession, discount_id: str) -> VolumeDiscount | None:
    return await db.get(VolumeDiscount, discount_id)


async def create_volume(
    db: AsyncSession,
    *,
    product_id: str,
    min_quantity: int,
    type: str,
    value: int,
) -> VolumeDiscount:
    discount = VolumeDiscount(
        product_id=product_id,
        min_quantity=min_quantity,
        type=type,
        value=value,
    )
    db.add(discount)
    await db.flush()
    await db.refresh(discount)
    return discount


async def delete_volume(db: AsyncSession, discount: VolumeDiscount) -> None:
    await db.delete(discount)
    await db.flush()


# --- Automatic discounts -----------------------------------------------------


async def list_automatic(
    db: AsyncSession, *, status: str | None = None, scope: str | None = None
) -> list[AutomaticDiscount]:
    stmt = select(AutomaticDiscount)
    if status:
        stmt = stmt.where(AutomaticDiscount.status == status)
    if scope:
        stmt = stmt.where(AutomaticDiscount.scope == scope)
    stmt = stmt.order_by(AutomaticDiscount.created_at.desc())
    rows = await db.execute(stmt)
    return list(rows.scalars().all())


async def get_automatic(db: AsyncSession, discount_id: str) -> AutomaticDiscount | None:
    return await db.get(AutomaticDiscount, discount_id)


async def create_automatic(db: AsyncSession, **fields) -> AutomaticDiscount:  # type: ignore[no-untyped-def]
    discount = AutomaticDiscount(**fields)
    db.add(discount)
    await db.flush()
    await db.refresh(discount)
    return discount


def apply_automatic_updates(discount: AutomaticDiscount, updates: dict[str, object]) -> None:
    for key, value in updates.items():
        setattr(discount, key, value)


async def delete_automatic(db: AsyncSession, discount: AutomaticDiscount) -> None:
    await db.delete(discount)
    await db.flush()
