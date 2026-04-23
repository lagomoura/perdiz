"""Public cart + coupon schemas (user-facing)."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)


# --- Customization selection payload (shape defined in
# docs/product/customization-model.md) --------------------------------------


class CustomizationSelection(_Strict):
    group_id: str = Field(min_length=26, max_length=26)
    option_ids: list[str] | None = None
    option_id: str | None = None  # used by single-option types (text/image/file)
    value: str | None = None  # ENGRAVING_TEXT
    file_id: str | None = None  # ENGRAVING_IMAGE / USER_FILE


# --- Cart items ------------------------------------------------------------


class CartItemAddIn(_Strict):
    product_id: str = Field(min_length=26, max_length=26)
    quantity: int = Field(ge=1, le=20)
    selections: list[CustomizationSelection] = Field(default_factory=list)


class CartItemUpdateIn(_Strict):
    quantity: int | None = Field(default=None, ge=1, le=20)
    selections: list[CustomizationSelection] | None = None


class CartItemOut(_Strict):
    id: str
    product_id: str
    name_snapshot: str
    image_url: str | None
    quantity: int
    unit_price_cents: int
    modifiers_total_cents: int
    line_total_cents: int
    customizations: dict[str, Any]
    warnings: list[str]


class CouponApplied(_Strict):
    code: str
    type: Literal["percentage", "fixed"]
    value: int


class CartOut(_Strict):
    id: str
    items: list[CartItemOut]
    subtotal_cents: int
    automatic_discounts_cents: int
    coupon: CouponApplied | None
    coupon_discount_cents: int
    shipping_cents: int
    total_cents: int
    currency: Literal["ARS"] = "ARS"


class CartEnvelope(_Strict):
    cart: CartOut


class ApplyCouponIn(_Strict):
    code: str = Field(min_length=1, max_length=80)
