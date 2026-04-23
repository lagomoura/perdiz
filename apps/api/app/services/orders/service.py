"""User-facing order queries — list + detail with owner enforcement."""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions import NotFoundError
from app.models.media_file import MediaFile
from app.models.order import Order
from app.models.order_item import OrderItem
from app.models.product_image import ProductImage
from app.models.user import User
from app.repositories import orders as orders_repo
from app.services.catalog import service as catalog_service

# The user list cap is intentionally small — users typically want their most
# recent orders. Paginate via cursor for power users.
DEFAULT_USER_LIMIT = 20
MAX_USER_LIMIT = 50


async def list_user_orders(
    db: AsyncSession, *, user: User, limit: int, cursor: str | None
) -> tuple[list[Order], dict[str, int], str | None]:
    """Return ``(orders, item_counts_by_order_id, next_cursor)``."""
    capped = max(1, min(limit, MAX_USER_LIMIT))
    orders = await orders_repo.list_for_user(db, user_id=user.id, limit=capped + 1, cursor=cursor)
    next_cursor = None
    if len(orders) > capped:
        next_cursor = orders_repo.encode_cursor(orders[capped - 1])
        orders = orders[:capped]
    counts = await _count_items(db, [o.id for o in orders])
    return orders, counts, next_cursor


async def get_user_order(
    db: AsyncSession, *, user: User, order_id: str
) -> tuple[Order, list[OrderItem], dict[str, str | None]]:
    order = await orders_repo.get_for_user(db, order_id=order_id, user_id=user.id)
    if order is None:
        raise NotFoundError("Pedido no encontrado.")
    items = await orders_repo.list_items_for_order(db, order_id=order.id)
    image_urls = await _primary_image_urls_for_products(db, [i.product_id for i in items])
    return order, items, image_urls


async def _count_items(db: AsyncSession, order_ids: list[str]) -> dict[str, int]:
    if not order_ids:
        return {}
    rows = await db.execute(
        select(OrderItem.order_id, func.sum(OrderItem.quantity))
        .where(OrderItem.order_id.in_(order_ids))
        .group_by(OrderItem.order_id)
    )
    out: dict[str, int] = {oid: 0 for oid in order_ids}
    for order_id, total in rows.all():
        out[order_id] = int(total or 0)
    return out


async def _primary_image_urls_for_products(
    db: AsyncSession, product_ids: list[str]
) -> dict[str, str | None]:
    if not product_ids:
        return {}
    rows = await db.execute(
        select(ProductImage)
        .where(ProductImage.product_id.in_(product_ids))
        .order_by(ProductImage.product_id, ProductImage.sort_order.asc())
    )
    seen: dict[str, str | None] = {pid: None for pid in product_ids}
    for pi in rows.scalars().all():
        if seen.get(pi.product_id) is None:
            mf = await db.get(MediaFile, pi.media_file_id)
            if mf is not None:
                seen[pi.product_id] = catalog_service.resolve_url(mf)
    return seen
