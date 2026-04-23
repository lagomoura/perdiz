"""Admin catalog request/response schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)


# --- Categories --------------------------------------------------------------


class CategoryAdmin(_Strict):
    id: str
    name: str
    slug: str
    parent_id: str | None
    description: str | None
    image_url: str | None
    sort_order: int
    status: Literal["active", "archived"]
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None


class CategoryCreateIn(_Strict):
    name: str = Field(min_length=1, max_length=120)
    slug: str = Field(min_length=1, max_length=120, pattern=r"^[a-z0-9][a-z0-9-]*$")
    parent_id: str | None = Field(default=None, max_length=26)
    description: str | None = None
    image_url: str | None = None
    sort_order: int = 0
    status: Literal["active", "archived"] = "active"


class CategoryUpdateIn(_Strict):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    slug: str | None = Field(
        default=None, min_length=1, max_length=120, pattern=r"^[a-z0-9][a-z0-9-]*$"
    )
    parent_id: str | None = Field(default=None, max_length=26)
    description: str | None = None
    image_url: str | None = None
    sort_order: int | None = None
    status: Literal["active", "archived"] | None = None


class CategoryAdminOut(_Strict):
    category: CategoryAdmin


class CategoryAdminListOut(_Strict):
    data: list[CategoryAdmin]


# --- Products ---------------------------------------------------------------


class ProductAdmin(_Strict):
    id: str
    category_id: str
    name: str
    slug: str
    description: str | None
    base_price_cents: int
    stock_mode: Literal["stocked", "print_on_demand"]
    stock_quantity: int | None
    lead_time_days: int | None
    weight_grams: int | None
    dimensions_mm: list[int] | None
    sku: str
    tags: list[str]
    status: Literal["draft", "active", "archived"]
    model_file_id: str | None
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None


class ProductCreateIn(_Strict):
    category_id: str = Field(min_length=26, max_length=26)
    name: str = Field(min_length=1, max_length=200)
    slug: str = Field(min_length=1, max_length=200, pattern=r"^[a-z0-9][a-z0-9-]*$")
    description: str | None = None
    base_price_cents: int = Field(ge=0)
    stock_mode: Literal["stocked", "print_on_demand"]
    stock_quantity: int | None = Field(default=None, ge=0)
    lead_time_days: int | None = Field(default=None, ge=1)
    weight_grams: int | None = Field(default=None, ge=0)
    dimensions_mm: list[int] | None = None
    sku: str = Field(min_length=1, max_length=60)
    tags: list[str] = Field(default_factory=list)
    status: Literal["draft", "active", "archived"] = "draft"
    model_file_id: str | None = Field(default=None, min_length=26, max_length=26)


class ProductUpdateIn(_Strict):
    category_id: str | None = Field(default=None, min_length=26, max_length=26)
    name: str | None = Field(default=None, min_length=1, max_length=200)
    slug: str | None = Field(
        default=None, min_length=1, max_length=200, pattern=r"^[a-z0-9][a-z0-9-]*$"
    )
    description: str | None = None
    base_price_cents: int | None = Field(default=None, ge=0)
    stock_mode: Literal["stocked", "print_on_demand"] | None = None
    stock_quantity: int | None = Field(default=None, ge=0)
    lead_time_days: int | None = Field(default=None, ge=1)
    weight_grams: int | None = Field(default=None, ge=0)
    dimensions_mm: list[int] | None = None
    sku: str | None = Field(default=None, min_length=1, max_length=60)
    tags: list[str] | None = None
    status: Literal["draft", "active", "archived"] | None = None
    model_file_id: str | None = Field(default=None, min_length=26, max_length=26)


class ProductStatusTransitionIn(_Strict):
    status: Literal["draft", "active", "archived"]


class ProductAdminOut(_Strict):
    product: ProductAdmin


class ProductAdminListOut(_Strict):
    data: list[ProductAdmin]
    count: int
