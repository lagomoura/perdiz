"""Public catalog service.

Read-only orchestration: filters, pagination, discount resolution, shaping of
products into the public DTOs. No caching yet — measure first.
"""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.exceptions import NotFoundError
from app.models.automatic_discount import AutomaticDiscount
from app.models.category import Category
from app.models.media_file import MediaFile
from app.models.product import Product
from app.models.product_image import ProductImage
from app.repositories import categories as categories_repo
from app.repositories import products as products_repo

# --- Discount maths ----------------------------------------------------------


def _apply_discount(base_cents: int, discount: AutomaticDiscount) -> int:
    """Return the resulting price after applying a single discount. Never
    below zero. ``value`` is 1..100 for percentage, centavos for fixed.
    """
    off = base_cents * discount.value // 100 if discount.type == "percentage" else discount.value
    return max(0, base_cents - off)


def _best_discounted_price(product: Product, candidates: list[AutomaticDiscount]) -> int | None:
    """Pick the discount that yields the lowest final price for this product.
    Return None if nothing applies.
    """
    applicable = [
        d
        for d in candidates
        if (d.scope == "product" and d.target_id == product.id)
        or (d.scope == "category" and d.target_id == product.category_id)
    ]
    if not applicable:
        return None
    best = min(_apply_discount(product.base_price_cents, d) for d in applicable)
    return best if best < product.base_price_cents else None


# --- Media URL resolution ----------------------------------------------------


def _resolve_url(media: MediaFile) -> str:
    """Public URL of a media file. Falls back to `{R2_PUBLIC_BASE_URL}/{key}`
    when the column isn't filled in.
    """
    if media.public_url:
        return media.public_url
    base = settings.r2_public_base_url.rstrip("/")
    return f"{base}/{media.storage_key}"


def _availability(stock_mode: str) -> str:
    return "in_stock" if stock_mode == "stocked" else "on_demand"


# --- Categories --------------------------------------------------------------


async def list_categories(db: AsyncSession) -> list[Category]:
    return await categories_repo.list_active(db)


async def get_category(db: AsyncSession, slug: str) -> Category:
    cat = await categories_repo.get_active_by_slug(db, slug)
    if cat is None:
        raise NotFoundError("Categoría no encontrada.")
    return cat


# --- Products ----------------------------------------------------------------


@dataclass
class ListedProduct:
    product: Product
    category: Category
    images: list[tuple[MediaFile, ProductImage]]
    is_customizable: bool
    discounted_price_cents: int | None


@dataclass
class ProductList:
    items: list[ListedProduct]
    next_cursor: str | None
    has_more: bool


async def list_products(db: AsyncSession, filters: products_repo.ProductListFilters) -> ProductList:
    products, has_more = await products_repo.list_public(db, filters)
    if not products:
        return ProductList(items=[], next_cursor=None, has_more=False)

    enrichment = await products_repo.fetch_list_enrichment(db, products)
    candidates = await products_repo.fetch_applicable_auto_discounts(
        db,
        product_ids=[p.id for p in products],
        category_ids=[p.category_id for p in products],
    )

    items: list[ListedProduct] = []
    for p in products:
        row = enrichment[p.id]
        discounted = _best_discounted_price(p, candidates)
        items.append(
            ListedProduct(
                product=p,
                category=row.category,
                images=row.images,
                is_customizable=row.is_customizable,
                discounted_price_cents=discounted,
            )
        )

    next_cursor = products[-1].id if has_more else None
    return ProductList(items=items, next_cursor=next_cursor, has_more=has_more)


@dataclass
class ProductDetail:
    product: Product
    category: Category
    images: list[tuple[MediaFile, ProductImage]]
    customization: list[tuple[object, list[object]]]
    volume_discounts: list[object]
    model_glb_url: str | None
    discounted_price_cents: int | None


async def get_product_detail(db: AsyncSession, slug: str) -> ProductDetail:
    product = await products_repo.get_public_detail_by_slug(db, slug)
    if product is None:
        raise NotFoundError("Producto no encontrado.")

    category = await db.get(Category, product.category_id)
    if category is None or category.status != "active":
        raise NotFoundError("Producto no encontrado.")

    images = await products_repo.fetch_images_for_product(db, product.id)
    customization = await products_repo.fetch_customization_for_product(db, product.id)
    volume_discounts = await products_repo.fetch_volume_discounts_for_product(db, product.id)
    glb_url = await products_repo.fetch_glb_url_for_product(db, product)
    candidates = await products_repo.fetch_applicable_auto_discounts(
        db, product_ids=[product.id], category_ids=[category.id]
    )
    discounted = _best_discounted_price(product, candidates)

    return ProductDetail(
        product=product,
        category=category,
        images=images,
        customization=customization,  # type: ignore[arg-type]
        volume_discounts=volume_discounts,  # type: ignore[arg-type]
        model_glb_url=glb_url,
        discounted_price_cents=discounted,
    )


# Re-exports for tests/consumers.
resolve_url = _resolve_url
availability_of = _availability
