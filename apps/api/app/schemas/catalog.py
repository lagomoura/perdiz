"""Public catalog schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)


# --- Categories --------------------------------------------------------------


class CategoryPublic(_Strict):
    id: str
    name: str
    slug: str
    description: str | None
    image_url: str | None
    sort_order: int


class CategoryListOut(_Strict):
    data: list[CategoryPublic]


class CategoryDetailOut(_Strict):
    category: CategoryPublic


# --- Products (shared) -------------------------------------------------------


class CategoryRef(_Strict):
    id: str
    name: str
    slug: str


class ProductImageOut(_Strict):
    url: str
    alt: str | None


Availability = Literal["in_stock", "on_demand"]


class ProductListItem(_Strict):
    id: str
    name: str
    slug: str
    price_cents: int
    discounted_price_cents: int | None
    currency: Literal["ARS"] = "ARS"
    images: list[ProductImageOut]
    category: CategoryRef
    availability: Availability
    customizable: bool
    tags: list[str]


class Pagination(_Strict):
    next_cursor: str | None
    has_more: bool
    count: int


class ProductListOut(_Strict):
    data: list[ProductListItem]
    pagination: Pagination


# --- Product detail ----------------------------------------------------------


class CustomizationOptionPublic(_Strict):
    id: str
    label: str
    price_modifier_cents: int
    is_default: bool
    is_available: bool
    sort_order: int
    metadata: dict[str, Any]


class CustomizationGroupPublic(_Strict):
    id: str
    name: str
    type: Literal["COLOR", "MATERIAL", "SIZE", "ENGRAVING_TEXT", "ENGRAVING_IMAGE", "USER_FILE"]
    required: bool
    selection_mode: Literal["single", "multiple"]
    sort_order: int
    metadata: dict[str, Any]
    options: list[CustomizationOptionPublic]


class VolumeDiscountPublic(_Strict):
    min_quantity: int
    type: Literal["percentage", "fixed"]
    value: int


class ProductDetail(_Strict):
    id: str
    name: str
    slug: str
    description_html: str | None
    base_price_cents: int
    discounted_price_cents: int | None
    currency: Literal["ARS"] = "ARS"
    category: CategoryRef
    images: list[ProductImageOut]
    model_glb_url: str | None
    stock_mode: Literal["stocked", "print_on_demand"]
    stock_quantity: int | None
    lead_time_days: int | None
    availability: Availability
    customizable: bool
    customization_groups: list[CustomizationGroupPublic]
    volume_discounts: list[VolumeDiscountPublic]
    tags: list[str]
    weight_grams: int | None
    dimensions_mm: list[int] | None
    created_at: datetime


class ProductDetailOut(_Strict):
    product: ProductDetail


# --- Query params ------------------------------------------------------------


Sort = Literal["newest", "price_asc", "price_desc", "relevance"]


class ProductListQuery(_Strict):
    q: str | None = None
    category: str | None = None
    price_min: int | None = Field(default=None, ge=0)
    price_max: int | None = Field(default=None, ge=0)
    availability: Availability | None = None
    customizable: bool | None = None
    sort: Sort = "newest"
    cursor: str | None = None
    limit: int = Field(default=24, ge=1, le=100)
