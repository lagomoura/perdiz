"""Admin customization / images / discounts schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)


CustomizationType = Literal[
    "COLOR", "MATERIAL", "SIZE", "ENGRAVING_TEXT", "ENGRAVING_IMAGE", "USER_FILE"
]
SelectionMode = Literal["single", "multiple"]


# --- Customization groups ----------------------------------------------------


class CustomizationGroupAdmin(_Strict):
    id: str
    product_id: str
    name: str
    type: CustomizationType
    required: bool
    selection_mode: SelectionMode
    sort_order: int
    metadata: dict[str, Any]
    created_at: datetime
    updated_at: datetime


class CustomizationGroupCreateIn(_Strict):
    name: str = Field(min_length=1, max_length=120)
    type: CustomizationType
    required: bool = False
    selection_mode: SelectionMode
    sort_order: int = 0
    metadata: dict[str, Any] = Field(default_factory=dict)


class CustomizationGroupUpdateIn(_Strict):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    type: CustomizationType | None = None
    required: bool | None = None
    selection_mode: SelectionMode | None = None
    sort_order: int | None = None
    metadata: dict[str, Any] | None = None


class CustomizationGroupOut(_Strict):
    group: CustomizationGroupAdmin


class CustomizationGroupListOut(_Strict):
    data: list[CustomizationGroupAdmin]


# --- Customization options ---------------------------------------------------


class CustomizationOptionAdmin(_Strict):
    id: str
    group_id: str
    label: str
    price_modifier_cents: int
    is_default: bool
    is_available: bool
    sort_order: int
    metadata: dict[str, Any]
    created_at: datetime
    updated_at: datetime


class CustomizationOptionCreateIn(_Strict):
    label: str = Field(min_length=1, max_length=120)
    price_modifier_cents: int = 0
    is_default: bool = False
    is_available: bool = True
    sort_order: int = 0
    metadata: dict[str, Any] = Field(default_factory=dict)


class CustomizationOptionUpdateIn(_Strict):
    label: str | None = Field(default=None, min_length=1, max_length=120)
    price_modifier_cents: int | None = None
    is_default: bool | None = None
    is_available: bool | None = None
    sort_order: int | None = None
    metadata: dict[str, Any] | None = None


class CustomizationOptionOut(_Strict):
    option: CustomizationOptionAdmin


class CustomizationOptionListOut(_Strict):
    data: list[CustomizationOptionAdmin]


# --- Product images ----------------------------------------------------------


class ProductImageAdmin(_Strict):
    id: str
    product_id: str
    media_file_id: str
    alt_text: str | None
    sort_order: int
    url: str | None


class ProductImageCreateIn(_Strict):
    media_file_id: str = Field(min_length=26, max_length=26)
    alt_text: str | None = Field(default=None, max_length=300)
    sort_order: int = 0


class ProductImageUpdateIn(_Strict):
    alt_text: str | None = Field(default=None, max_length=300)
    sort_order: int | None = None


class ProductImageOut(_Strict):
    image: ProductImageAdmin


class ProductImageListOut(_Strict):
    data: list[ProductImageAdmin]


# --- Volume discounts --------------------------------------------------------


DiscountType = Literal["percentage", "fixed"]


class VolumeDiscountAdmin(_Strict):
    id: str
    product_id: str
    min_quantity: int
    type: DiscountType
    value: int


class VolumeDiscountCreateIn(_Strict):
    min_quantity: int = Field(ge=2)
    type: DiscountType
    value: int = Field(gt=0)


class VolumeDiscountOut(_Strict):
    discount: VolumeDiscountAdmin


class VolumeDiscountListOut(_Strict):
    data: list[VolumeDiscountAdmin]


# --- Automatic discounts -----------------------------------------------------


DiscountScope = Literal["category", "product"]
DiscountStatus = Literal["active", "disabled"]


class AutomaticDiscountAdmin(_Strict):
    id: str
    name: str
    type: DiscountType
    value: int
    scope: DiscountScope
    target_id: str
    valid_from: datetime | None
    valid_until: datetime | None
    status: DiscountStatus
    created_at: datetime
    updated_at: datetime


class AutomaticDiscountCreateIn(_Strict):
    name: str = Field(min_length=1, max_length=200)
    type: DiscountType
    value: int = Field(gt=0)
    scope: DiscountScope
    target_id: str = Field(min_length=26, max_length=26)
    valid_from: datetime | None = None
    valid_until: datetime | None = None
    status: DiscountStatus = "active"


class AutomaticDiscountUpdateIn(_Strict):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    type: DiscountType | None = None
    value: int | None = Field(default=None, gt=0)
    scope: DiscountScope | None = None
    target_id: str | None = Field(default=None, min_length=26, max_length=26)
    valid_from: datetime | None = None
    valid_until: datetime | None = None
    status: DiscountStatus | None = None


class AutomaticDiscountOut(_Strict):
    discount: AutomaticDiscountAdmin


class AutomaticDiscountListOut(_Strict):
    data: list[AutomaticDiscountAdmin]
