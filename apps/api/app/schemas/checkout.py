"""Checkout + order schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)


class ShippingAddressIn(_Strict):
    full_name: str = Field(min_length=1, max_length=120)
    street: str = Field(min_length=1, max_length=200)
    street_number: str = Field(min_length=1, max_length=20)
    unit: str | None = Field(default=None, max_length=40)
    city: str = Field(min_length=1, max_length=80)
    province: str = Field(min_length=1, max_length=80)
    postal_code: str = Field(min_length=1, max_length=20)
    country: str = Field(default="AR", min_length=2, max_length=2)
    phone: str = Field(min_length=6, max_length=30)
    notes: str | None = Field(default=None, max_length=500)


ShippingMethod = Literal["pickup", "standard"]
PaymentProviderName = Literal["mercadopago"]


class CheckoutIn(_Strict):
    shipping_address: ShippingAddressIn
    shipping_method: ShippingMethod
    payment_provider: PaymentProviderName = "mercadopago"


class CheckoutOut(_Strict):
    order_id: str
    payment_id: str
    provider: PaymentProviderName
    redirect_url: str
    total_cents: int
    currency: Literal["ARS"] = "ARS"


class OrderItemOut(_Strict):
    id: str
    product_id: str
    product_name_snapshot: str
    quantity: int
    unit_price_cents: int
    modifiers_total_cents: int
    line_total_cents: int


class OrderOut(_Strict):
    id: str
    status: str
    subtotal_cents: int
    discount_cents: int
    shipping_cents: int
    total_cents: int
    currency: str
    placed_at: datetime
    paid_at: datetime | None
    items: list[OrderItemOut]
