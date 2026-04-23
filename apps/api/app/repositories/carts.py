"""Cart + cart_item repository."""

from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.cart import Cart
from app.models.cart_item import CartItem


async def get_open_cart(db: AsyncSession, user_id: str) -> Cart | None:
    row = await db.execute(select(Cart).where(Cart.user_id == user_id, Cart.status == "open"))
    return row.scalar_one_or_none()


async def ensure_open_cart(db: AsyncSession, user_id: str) -> Cart:
    cart = await get_open_cart(db, user_id)
    if cart is not None:
        return cart
    cart = Cart(user_id=user_id, status="open")
    db.add(cart)
    await db.flush()
    await db.refresh(cart)
    return cart


async def list_items(db: AsyncSession, cart_id: str) -> list[CartItem]:
    rows = await db.execute(
        select(CartItem).where(CartItem.cart_id == cart_id).order_by(CartItem.added_at.asc())
    )
    return list(rows.scalars().all())


async def get_item(db: AsyncSession, item_id: str) -> CartItem | None:
    return await db.get(CartItem, item_id)


async def create_item(
    db: AsyncSession,
    *,
    cart_id: str,
    product_id: str,
    quantity: int,
    unit_price_cents: int,
    modifiers_total_cents: int,
    customizations: dict[str, Any],
) -> CartItem:
    item = CartItem(
        cart_id=cart_id,
        product_id=product_id,
        quantity=quantity,
        unit_price_cents=unit_price_cents,
        modifiers_total_cents=modifiers_total_cents,
        customizations=customizations,
    )
    db.add(item)
    await db.flush()
    await db.refresh(item)
    return item


async def delete_item(db: AsyncSession, item: CartItem) -> None:
    await db.delete(item)
    await db.flush()
