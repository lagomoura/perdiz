"""User-facing cart service.

Coordinates: fetch/create cart, resolve customizations, dedupe line
items, compute totals on each read, apply/remove coupon.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions import BusinessRuleViolation, NotFoundError, ValidationError
from app.models.cart import Cart
from app.models.cart_item import CartItem
from app.models.coupon import Coupon
from app.models.media_file import MediaFile
from app.models.product import Product
from app.models.product_image import ProductImage
from app.models.user import User
from app.repositories import carts as carts_repo
from app.repositories import coupons as coupons_repo
from app.services.cart import customization as customization_service
from app.services.cart import pricing as pricing_service
from app.services.catalog import service as catalog_service


@dataclass
class CartView:
    cart: Cart
    items: list[CartItem]
    coupon: Coupon | None
    totals: pricing_service.CartTotals
    item_context: dict[str, tuple[Product, str | None]]
    # item_context: item_id → (product, image_url)


async def get_or_create(db: AsyncSession, *, user: User) -> Cart:
    return await carts_repo.ensure_open_cart(db, user.id)


async def render(db: AsyncSession, *, user: User) -> CartView:
    cart = await get_or_create(db, user=user)
    items = await carts_repo.list_items(db, cart.id)
    coupon = await coupons_repo.get_by_id(db, cart.coupon_id) if cart.coupon_id else None
    totals = await pricing_service.compute_totals(db, items=items, coupon=coupon)

    # Resolve product + primary image url for the DTO. One query each batch.
    ctx: dict[str, tuple[Product, str | None]] = {}
    if items:
        product_ids = list({i.product_id for i in items})
        products_by_id: dict[str, Product] = {}
        for pid in product_ids:
            p = await db.get(Product, pid)
            if p is not None:
                products_by_id[pid] = p
        image_urls: dict[str, str | None] = await _primary_image_urls(db, product_ids)
        for item in items:
            prod = products_by_id.get(item.product_id)
            if prod is not None:
                ctx[item.id] = (prod, image_urls.get(item.product_id))

    return CartView(cart=cart, items=items, coupon=coupon, totals=totals, item_context=ctx)


async def add_item(
    db: AsyncSession,
    *,
    user: User,
    product_id: str,
    quantity: int,
    raw_selections: list[dict[str, Any]],
) -> Cart:
    cart = await get_or_create(db, user=user)
    product = await db.get(Product, product_id)
    if product is None or product.status != "active" or product.deleted_at is not None:
        raise NotFoundError("Producto no encontrado.")
    if (
        product.stock_mode == "stocked"
        and product.stock_quantity is not None
        and product.stock_quantity < quantity
    ):
        raise BusinessRuleViolation(
            "No hay suficiente stock.",
            details={"code": "CART_ITEM_OUT_OF_STOCK"},
        )

    resolved = await customization_service.validate_and_resolve(
        db,
        product_id=product.id,
        actor_id=user.id,
        raw_selections=[s for s in raw_selections],
    )

    # Dedupe: if there's already an item with the same product + same
    # fingerprint, just bump the quantity.
    fingerprint = customization_service.selections_fingerprint(resolved.selections)
    existing = await _find_item_with_fingerprint(db, cart.id, product.id, fingerprint)
    if existing is not None:
        new_qty = existing.quantity + quantity
        if new_qty > 20:
            raise BusinessRuleViolation(
                "El máximo por producto es 20 unidades.",
                details={"code": "CART_ITEM_QUANTITY_EXCEEDED"},
            )
        existing.quantity = new_qty
        await db.flush()
    else:
        customizations_json = {
            "selections": resolved.selections,
            "resolved_modifier_cents": resolved.resolved_modifier_cents,
        }
        await carts_repo.create_item(
            db,
            cart_id=cart.id,
            product_id=product.id,
            quantity=quantity,
            unit_price_cents=product.base_price_cents,
            modifiers_total_cents=resolved.resolved_modifier_cents,
            customizations=customizations_json,
        )

    await db.commit()
    return cart


async def update_item(
    db: AsyncSession,
    *,
    user: User,
    item_id: str,
    quantity: int | None,
    raw_selections: list[dict[str, Any]] | None,
) -> Cart:
    cart = await _user_cart_or_404(db, user)
    item = await carts_repo.get_item(db, item_id)
    if item is None or item.cart_id != cart.id:
        raise NotFoundError("Ítem no encontrado.")

    if quantity is not None:
        if quantity < 1 or quantity > 20:
            raise ValidationError(
                "La cantidad debe estar entre 1 y 20.",
                details={"field": "quantity"},
            )
        item.quantity = quantity

    if raw_selections is not None:
        resolved = await customization_service.validate_and_resolve(
            db,
            product_id=item.product_id,
            actor_id=user.id,
            raw_selections=raw_selections,
        )
        # Re-snapshot modifier to match the new selection set. Unit price is
        # kept as the original snapshot on purpose (docs: price changes
        # during cart life surface at checkout, not on every mutation).
        item.modifiers_total_cents = resolved.resolved_modifier_cents
        item.customizations = {
            "selections": resolved.selections,
            "resolved_modifier_cents": resolved.resolved_modifier_cents,
        }

    await db.flush()
    await db.commit()
    return cart


async def remove_item(db: AsyncSession, *, user: User, item_id: str) -> Cart:
    cart = await _user_cart_or_404(db, user)
    item = await carts_repo.get_item(db, item_id)
    if item is None or item.cart_id != cart.id:
        raise NotFoundError("Ítem no encontrado.")
    await carts_repo.delete_item(db, item)
    await db.commit()
    return cart


async def apply_coupon(db: AsyncSession, *, user: User, code: str) -> Cart:
    cart = await get_or_create(db, user=user)
    coupon = await coupons_repo.get_by_code(db, code)
    if coupon is None or coupon.status != "active":
        raise ValidationError(
            "El código no es válido.",
            details={"code": "COUPON_NOT_FOUND", "field": "code"},
        )
    now = datetime.now(tz=UTC)
    if coupon.valid_from and coupon.valid_from > now:
        raise ValidationError(
            "El cupón todavía no está vigente.",
            details={"code": "COUPON_NOT_YET_VALID", "field": "code"},
        )
    if coupon.valid_until and coupon.valid_until < now:
        raise ValidationError(
            "El cupón expiró.",
            details={"code": "COUPON_EXPIRED", "field": "code"},
        )

    items = await carts_repo.list_items(db, cart.id)
    subtotal = sum((i.unit_price_cents + i.modifiers_total_cents) * i.quantity for i in items)
    if subtotal < coupon.min_order_cents:
        raise ValidationError(
            "El total del carrito no alcanza el mínimo del cupón.",
            details={"code": "COUPON_MIN_ORDER_NOT_MET", "field": "code"},
        )

    cart.coupon_id = coupon.id
    await db.flush()
    await db.commit()
    return cart


async def remove_coupon(db: AsyncSession, *, user: User) -> Cart:
    cart = await get_or_create(db, user=user)
    cart.coupon_id = None
    await db.flush()
    await db.commit()
    return cart


# --- Helpers ----------------------------------------------------------------


async def _user_cart_or_404(db: AsyncSession, user: User) -> Cart:
    cart = await carts_repo.get_open_cart(db, user.id)
    if cart is None:
        raise NotFoundError("No tenés un carrito abierto.")
    return cart


async def _find_item_with_fingerprint(
    db: AsyncSession, cart_id: str, product_id: str, fingerprint: str
) -> CartItem | None:
    rows = await db.execute(
        select(CartItem).where(CartItem.cart_id == cart_id, CartItem.product_id == product_id)
    )
    for item in rows.scalars().all():
        sels = (item.customizations or {}).get("selections", [])
        if customization_service.selections_fingerprint(sels) == fingerprint:
            return item
    return None


async def _primary_image_urls(db: AsyncSession, product_ids: list[str]) -> dict[str, str | None]:
    """First image url (sorted by sort_order) per product; None if absent."""
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


def _fingerprint_from_saved(item: CartItem) -> str:
    """Used by tests and maintenance."""
    return customization_service.selections_fingerprint(
        (item.customizations or {}).get("selections", [])
    )
