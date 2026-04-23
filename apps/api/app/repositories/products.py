"""Product repository for public listing and detail queries."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import Exists, and_, exists, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.elements import ColumnElement

from app.models.automatic_discount import AutomaticDiscount
from app.models.category import Category
from app.models.customization_group import CustomizationGroup
from app.models.customization_option import CustomizationOption
from app.models.media_file import MediaFile
from app.models.product import Product
from app.models.product_image import ProductImage
from app.models.volume_discount import VolumeDiscount


@dataclass
class ProductListFilters:
    q: str | None = None
    category_slug: str | None = None
    price_min: int | None = None
    price_max: int | None = None
    availability: str | None = None  # "in_stock" or "on_demand"
    customizable: bool | None = None
    sort: str = "newest"  # newest | price_asc | price_desc | relevance
    cursor: str | None = None
    limit: int = 24


@dataclass
class ProductListRow:
    product: Product
    category: Category
    images: list[tuple[MediaFile, ProductImage]]
    is_customizable: bool


def _customization_exists() -> Exists:
    return exists().where(CustomizationGroup.product_id == Product.id)


def _availability_from_stock_mode(stock_mode: str) -> str:
    return "in_stock" if stock_mode == "stocked" else "on_demand"


def _apply_filters(stmt, filters: ProductListFilters):  # type: ignore[no-untyped-def]
    if filters.category_slug:
        stmt = stmt.join(Category, Product.category_id == Category.id).where(
            Category.slug == filters.category_slug,
            Category.status == "active",
            Category.deleted_at.is_(None),
        )
    if filters.price_min is not None:
        stmt = stmt.where(Product.base_price_cents >= filters.price_min)
    if filters.price_max is not None:
        stmt = stmt.where(Product.base_price_cents <= filters.price_max)
    if filters.availability == "in_stock":
        stmt = stmt.where(Product.stock_mode == "stocked")
    elif filters.availability == "on_demand":
        stmt = stmt.where(Product.stock_mode == "print_on_demand")
    if filters.customizable is True:
        stmt = stmt.where(_customization_exists())
    elif filters.customizable is False:
        stmt = stmt.where(~_customization_exists())
    if filters.q:
        ts_query = func.plainto_tsquery("spanish", filters.q)
        stmt = stmt.where(
            or_(
                Product.search_tsv.op("@@")(ts_query),
                Product.tags.contains([filters.q]),
            )
        )
    return stmt


async def _apply_sort_and_cursor(db: AsyncSession, stmt, filters: ProductListFilters):  # type: ignore[no-untyped-def]
    cursor_id = filters.cursor
    if filters.sort in ("price_asc", "price_desc"):
        asc = filters.sort == "price_asc"
        stmt = stmt.order_by(
            Product.base_price_cents.asc() if asc else Product.base_price_cents.desc(),
            Product.id.asc() if asc else Product.id.desc(),
        )
        if cursor_id:
            cursor_product = await db.get(Product, cursor_id)
            if cursor_product:
                price_cmp = (
                    Product.base_price_cents > cursor_product.base_price_cents
                    if asc
                    else Product.base_price_cents < cursor_product.base_price_cents
                )
                id_cmp = Product.id > cursor_product.id if asc else Product.id < cursor_product.id
                stmt = stmt.where(
                    or_(
                        price_cmp,
                        and_(
                            Product.base_price_cents == cursor_product.base_price_cents,
                            id_cmp,
                        ),
                    )
                )
        return stmt
    if filters.sort == "relevance" and filters.q:
        rank = func.ts_rank(Product.search_tsv, func.plainto_tsquery("spanish", filters.q)).label(
            "rank"
        )
        stmt = stmt.order_by(rank.desc(), Product.id.desc())
        if cursor_id:
            stmt = stmt.where(Product.id < cursor_id)
        return stmt
    # newest (default)
    stmt = stmt.order_by(Product.id.desc())
    if cursor_id:
        stmt = stmt.where(Product.id < cursor_id)
    return stmt


async def list_public(db: AsyncSession, filters: ProductListFilters) -> tuple[list[Product], bool]:
    """Return (products, has_more). Does not fetch category/images — do that via
    a follow-up query to keep the listing SQL focused.
    """
    stmt = select(Product).where(
        Product.status == "active",
        Product.deleted_at.is_(None),
    )
    stmt = _apply_filters(stmt, filters)
    stmt = await _apply_sort_and_cursor(db, stmt, filters)
    # Fetch limit+1 to detect has_more.
    stmt = stmt.limit(filters.limit + 1)
    result = await db.execute(stmt)
    rows = list(result.scalars().all())
    has_more = len(rows) > filters.limit
    return rows[: filters.limit], has_more


async def fetch_list_enrichment(
    db: AsyncSession, products: list[Product]
) -> dict[str, ProductListRow]:
    """Given a list of products, fetch category, primary image and
    customization-flag for each. Single query per resource, avoiding N+1.
    Returns a mapping product_id → ProductListRow.
    """
    if not products:
        return {}

    product_ids = [p.id for p in products]
    category_ids = {p.category_id for p in products}

    # Categories.
    cat_rows = await db.execute(select(Category).where(Category.id.in_(category_ids)))
    by_cat_id = {c.id: c for c in cat_rows.scalars().all()}

    # Product images (all of them so we can order) + media_file.
    img_rows = await db.execute(
        select(ProductImage, MediaFile)
        .join(MediaFile, ProductImage.media_file_id == MediaFile.id)
        .where(ProductImage.product_id.in_(product_ids))
        .order_by(ProductImage.product_id, ProductImage.sort_order.asc())
    )
    images_by_product: dict[str, list[tuple[MediaFile, ProductImage]]] = {}
    for pi, mf in img_rows.all():
        images_by_product.setdefault(pi.product_id, []).append((mf, pi))

    # Customization-exists flag.
    cust_rows = await db.execute(
        select(CustomizationGroup.product_id)
        .where(CustomizationGroup.product_id.in_(product_ids))
        .distinct()
    )
    has_customization = {row[0] for row in cust_rows.all()}

    out: dict[str, ProductListRow] = {}
    for p in products:
        out[p.id] = ProductListRow(
            product=p,
            category=by_cat_id[p.category_id],
            images=images_by_product.get(p.id, []),
            is_customizable=p.id in has_customization,
        )
    return out


async def get_public_detail_by_slug(db: AsyncSession, slug: str) -> Product | None:
    """Full product detail including customization groups/options and images.

    Uses selectinload for eager fetching (avoids N+1). Still needs a follow-up
    query for volume_discounts and the derived GLB URL (done in the service).
    """
    stmt = (
        select(Product)
        .where(
            Product.slug == slug,
            Product.status == "active",
            Product.deleted_at.is_(None),
        )
        .options()  # relationships are not declared on the model yet; we fetch manually below
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def fetch_customization_for_product(
    db: AsyncSession, product_id: str
) -> list[tuple[CustomizationGroup, list[CustomizationOption]]]:
    group_rows = await db.execute(
        select(CustomizationGroup)
        .where(CustomizationGroup.product_id == product_id)
        .order_by(CustomizationGroup.sort_order.asc(), CustomizationGroup.name.asc())
    )
    groups = list(group_rows.scalars().all())
    if not groups:
        return []

    group_ids = [g.id for g in groups]
    opt_rows = await db.execute(
        select(CustomizationOption)
        .where(CustomizationOption.group_id.in_(group_ids))
        .order_by(CustomizationOption.sort_order.asc(), CustomizationOption.label.asc())
    )
    options_by_group: dict[str, list[CustomizationOption]] = {}
    for opt in opt_rows.scalars().all():
        options_by_group.setdefault(opt.group_id, []).append(opt)

    return [(g, options_by_group.get(g.id, [])) for g in groups]


async def fetch_images_for_product(
    db: AsyncSession, product_id: str
) -> list[tuple[MediaFile, ProductImage]]:
    rows = await db.execute(
        select(ProductImage, MediaFile)
        .join(MediaFile, ProductImage.media_file_id == MediaFile.id)
        .where(ProductImage.product_id == product_id)
        .order_by(ProductImage.sort_order.asc())
    )
    return [(mf, pi) for pi, mf in rows.all()]


async def fetch_glb_url_for_product(db: AsyncSession, product: Product) -> str | None:
    """Return the public URL of the GLB derived from the product's source STL,
    or the public URL of the file itself if it is already a GLB.
    """
    if not product.model_file_id:
        return None

    source = await db.get(MediaFile, product.model_file_id)
    if source is None:
        return None
    if source.kind == "model_glb":
        return source.public_url

    # Look for a GLB derived from this STL.
    derived_rows = await db.execute(
        select(MediaFile).where(
            MediaFile.derived_from_id == source.id,
            MediaFile.kind == "model_glb",
        )
    )
    derived = derived_rows.scalars().first()
    return derived.public_url if derived else None


async def fetch_volume_discounts_for_product(
    db: AsyncSession, product_id: str
) -> list[VolumeDiscount]:
    rows = await db.execute(
        select(VolumeDiscount)
        .where(VolumeDiscount.product_id == product_id)
        .order_by(VolumeDiscount.min_quantity.asc())
    )
    return list(rows.scalars().all())


async def fetch_applicable_auto_discounts(
    db: AsyncSession, *, product_ids: list[str], category_ids: list[str]
) -> list[AutomaticDiscount]:
    """All active automatic discounts that could apply to any of the given
    products/categories, inside their valid-time window. Caller picks the
    best one per product.
    """
    if not product_ids and not category_ids:
        return []
    now = datetime.now(tz=UTC)
    scope_clauses: list[ColumnElement[bool]] = []
    if product_ids:
        scope_clauses.append(
            and_(
                AutomaticDiscount.scope == "product",
                AutomaticDiscount.target_id.in_(product_ids),
            )
        )
    if category_ids:
        scope_clauses.append(
            and_(
                AutomaticDiscount.scope == "category",
                AutomaticDiscount.target_id.in_(category_ids),
            )
        )
    rows = await db.execute(
        select(AutomaticDiscount).where(
            AutomaticDiscount.status == "active",
            or_(AutomaticDiscount.valid_from.is_(None), AutomaticDiscount.valid_from <= now),
            or_(
                AutomaticDiscount.valid_until.is_(None),
                AutomaticDiscount.valid_until >= now,
            ),
            or_(*scope_clauses),
        )
    )
    return list(rows.scalars().all())
