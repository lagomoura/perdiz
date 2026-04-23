"""Cart pricing: totals = subtotal - automatic - coupon (>= 0)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.cart_item import CartItem
from app.models.coupon import Coupon
from app.models.product import Product
from app.repositories import products as products_repo
from app.services.catalog import service as catalog_service


@dataclass
class CartTotals:
    subtotal_cents: int
    automatic_discounts_cents: int
    coupon_discount_cents: int
    shipping_cents: int
    total_cents: int


def _line_total(item: CartItem) -> int:
    return (item.unit_price_cents + item.modifiers_total_cents) * item.quantity


def _apply_value(base_cents: int, discount_type: str, value: int) -> int:
    off = base_cents * value // 100 if discount_type == "percentage" else value
    return max(0, min(base_cents, off))


async def _compute_auto_discount(db: AsyncSession, *, items: list[CartItem], subtotal: int) -> int:
    if not items:
        return 0
    products_by_id: dict[str, Product] = {}
    for pid in [i.product_id for i in items]:
        prod = await db.get(Product, pid)
        if prod is not None:
            products_by_id[pid] = prod
    category_ids = list({p.category_id for p in products_by_id.values()})
    candidates = await products_repo.fetch_applicable_auto_discounts(
        db, product_ids=list(products_by_id.keys()), category_ids=category_ids
    )
    total = 0
    for item in items:
        prod = products_by_id.get(item.product_id)
        if prod is None:
            continue
        best_price = catalog_service._best_discounted_price(prod, candidates)
        if best_price is None:
            continue
        per_unit_saving = max(0, prod.base_price_cents - best_price)
        total += per_unit_saving * item.quantity
    return min(total, subtotal)


async def _compute_coupon_discount(
    db: AsyncSession,
    *,
    coupon: Coupon,
    items: list[CartItem],
    subtotal: int,
    auto_discount: int,
) -> tuple[int, int]:
    """Return ``(coupon_discount, adjusted_auto_discount)``.

    When ``stacks_with_automatic`` is False and a coupon beats the auto
    discount, we drop the auto and apply only the coupon (and vice-versa).
    """
    if coupon.applicable_category_ids or coupon.applicable_product_ids:
        base = await _subtotal_for_coupon_scoped(db, coupon, items)
    else:
        base = subtotal

    if coupon.stacks_with_automatic:
        after_auto = max(0, base - auto_discount)
        return _apply_value(after_auto, coupon.type, coupon.value), auto_discount

    hypothetical = min(
        base * coupon.value // 100 if coupon.type == "percentage" else coupon.value,
        base,
    )
    if hypothetical > auto_discount:
        return hypothetical, 0
    return 0, auto_discount


async def compute_totals(
    db: AsyncSession,
    *,
    items: list[CartItem],
    coupon: Coupon | None,
) -> CartTotals:
    subtotal = sum(_line_total(item) for item in items)
    auto_discount = await _compute_auto_discount(db, items=items, subtotal=subtotal)
    coupon_discount = 0
    if coupon is not None and _coupon_is_valid_now(coupon):
        coupon_discount, auto_discount = await _compute_coupon_discount(
            db,
            coupon=coupon,
            items=items,
            subtotal=subtotal,
            auto_discount=auto_discount,
        )

    total = max(0, subtotal - auto_discount - coupon_discount)
    return CartTotals(
        subtotal_cents=subtotal,
        automatic_discounts_cents=auto_discount,
        coupon_discount_cents=coupon_discount,
        shipping_cents=0,
        total_cents=total,
    )


def _coupon_is_valid_now(coupon: Coupon) -> bool:
    if coupon.status != "active":
        return False
    now = datetime.now(tz=UTC)
    if coupon.valid_from and coupon.valid_from > now:
        return False
    return not (coupon.valid_until and coupon.valid_until < now)


async def _subtotal_for_coupon_scoped(
    db: AsyncSession, coupon: Coupon, items: list[CartItem]
) -> int:
    applicable_product_ids = set(coupon.applicable_product_ids)
    applicable_category_ids = set(coupon.applicable_category_ids)
    total = 0
    for item in items:
        prod = await db.get(Product, item.product_id)
        if prod is None:
            continue
        if item.product_id in applicable_product_ids or prod.category_id in applicable_category_ids:
            total += _line_total(item)
    return total
