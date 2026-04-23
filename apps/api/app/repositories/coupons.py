"""Coupon repository — admin CRUD and user-side lookup by code."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.coupon import Coupon


async def list_all(db: AsyncSession, *, status: str | None = None) -> list[Coupon]:
    stmt = select(Coupon)
    if status:
        stmt = stmt.where(Coupon.status == status)
    stmt = stmt.order_by(Coupon.created_at.desc())
    return list((await db.execute(stmt)).scalars().all())


async def get_by_id(db: AsyncSession, coupon_id: str) -> Coupon | None:
    return await db.get(Coupon, coupon_id)


async def get_by_code(db: AsyncSession, code: str) -> Coupon | None:
    row = await db.execute(select(Coupon).where(Coupon.code == code.lower()))
    return row.scalar_one_or_none()


async def create(db: AsyncSession, **fields) -> Coupon:  # type: ignore[no-untyped-def]
    # Store code lowercase for case-insensitive match.
    fields["code"] = fields["code"].lower()
    coupon = Coupon(**fields)
    db.add(coupon)
    await db.flush()
    await db.refresh(coupon)
    return coupon


def apply_updates(coupon: Coupon, updates: dict[str, object]) -> None:
    if "code" in updates and isinstance(updates["code"], str):
        updates["code"] = updates["code"].lower()
    for key, value in updates.items():
        setattr(coupon, key, value)


async def delete(db: AsyncSession, coupon: Coupon) -> None:
    await db.delete(coupon)
    await db.flush()
