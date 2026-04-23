"""Public product endpoints: listing with filters/FTS and detail by slug."""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Query

from app.api.deps import DbSession
from app.repositories.products import ProductListFilters
from app.schemas.catalog import (
    Availability,
    CategoryRef,
    CustomizationGroupPublic,
    CustomizationOptionPublic,
    Pagination,
    ProductDetail,
    ProductDetailOut,
    ProductImageOut,
    ProductListItem,
    ProductListOut,
    Sort,
    VolumeDiscountPublic,
)
from app.services.catalog import service as catalog_service

router = APIRouter(prefix="/products", tags=["catalog"])


def _images_to_dto(images: list[Any]) -> list[ProductImageOut]:
    return [
        ProductImageOut(url=catalog_service.resolve_url(mf), alt=pi.alt_text) for mf, pi in images
    ]


@router.get("", response_model=ProductListOut)
async def list_products(
    db: DbSession,
    q: Annotated[str | None, Query(max_length=200)] = None,
    category: Annotated[str | None, Query(max_length=120)] = None,
    price_min: Annotated[int | None, Query(ge=0)] = None,
    price_max: Annotated[int | None, Query(ge=0)] = None,
    availability: Annotated[Availability | None, Query()] = None,
    customizable: Annotated[bool | None, Query()] = None,
    sort: Annotated[Sort, Query()] = "newest",
    cursor: Annotated[str | None, Query(max_length=40)] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 24,
) -> ProductListOut:
    filters = ProductListFilters(
        q=q,
        category_slug=category,
        price_min=price_min,
        price_max=price_max,
        availability=availability,
        customizable=customizable,
        sort=sort,
        cursor=cursor,
        limit=limit,
    )
    listing = await catalog_service.list_products(db, filters)

    data: list[ProductListItem] = []
    for item in listing.items:
        data.append(
            ProductListItem(
                id=item.product.id,
                name=item.product.name,
                slug=item.product.slug,
                price_cents=item.product.base_price_cents,
                discounted_price_cents=item.discounted_price_cents,
                images=_images_to_dto(item.images),
                category=CategoryRef(
                    id=item.category.id, name=item.category.name, slug=item.category.slug
                ),
                availability=catalog_service.availability_of(item.product.stock_mode),  # type: ignore[arg-type]
                customizable=item.is_customizable,
                tags=list(item.product.tags or []),
            )
        )
    return ProductListOut(
        data=data,
        pagination=Pagination(
            next_cursor=listing.next_cursor,
            has_more=listing.has_more,
            count=len(data),
        ),
    )


@router.get("/{slug}", response_model=ProductDetailOut)
async def get_product(slug: str, db: DbSession) -> ProductDetailOut:
    d = await catalog_service.get_product_detail(db, slug)
    p = d.product

    groups_out: list[CustomizationGroupPublic] = []
    for g, options in d.customization:
        groups_out.append(
            CustomizationGroupPublic(
                id=g.id,  # type: ignore[attr-defined]
                name=g.name,  # type: ignore[attr-defined]
                type=g.type,  # type: ignore[attr-defined]
                required=g.required,  # type: ignore[attr-defined]
                selection_mode=g.selection_mode,  # type: ignore[attr-defined]
                sort_order=g.sort_order,  # type: ignore[attr-defined]
                metadata=g.group_metadata,  # type: ignore[attr-defined]
                options=[
                    CustomizationOptionPublic(
                        id=o.id,  # type: ignore[attr-defined]
                        label=o.label,  # type: ignore[attr-defined]
                        price_modifier_cents=o.price_modifier_cents,  # type: ignore[attr-defined]
                        is_default=o.is_default,  # type: ignore[attr-defined]
                        is_available=o.is_available,  # type: ignore[attr-defined]
                        sort_order=o.sort_order,  # type: ignore[attr-defined]
                        metadata=o.option_metadata,  # type: ignore[attr-defined]
                    )
                    for o in options
                ],
            )
        )

    detail = ProductDetail(
        id=p.id,
        name=p.name,
        slug=p.slug,
        description_html=p.description,
        base_price_cents=p.base_price_cents,
        discounted_price_cents=d.discounted_price_cents,
        category=CategoryRef(id=d.category.id, name=d.category.name, slug=d.category.slug),
        images=_images_to_dto(d.images),
        model_glb_url=d.model_glb_url,
        stock_mode=p.stock_mode,  # type: ignore[arg-type]
        stock_quantity=p.stock_quantity,
        lead_time_days=p.lead_time_days,
        availability=catalog_service.availability_of(p.stock_mode),  # type: ignore[arg-type]
        customizable=bool(d.customization),
        customization_groups=groups_out,
        volume_discounts=[
            VolumeDiscountPublic(
                min_quantity=v.min_quantity,  # type: ignore[attr-defined]
                type=v.type,  # type: ignore[attr-defined]
                value=v.value,  # type: ignore[attr-defined]
            )
            for v in d.volume_discounts
        ],
        tags=list(p.tags or []),
        weight_grams=p.weight_grams,
        dimensions_mm=list(p.dimensions_mm) if p.dimensions_mm else None,
        created_at=p.created_at,
    )
    return ProductDetailOut(product=detail)
