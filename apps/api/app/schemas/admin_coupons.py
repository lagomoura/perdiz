"""Admin coupon schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)


CouponType = Literal["percentage", "fixed"]
CouponStatus = Literal["active", "disabled"]


class CouponAdmin(_Strict):
    id: str
    code: str
    type: CouponType
    value: int
    min_order_cents: int
    valid_from: datetime | None
    valid_until: datetime | None
    max_uses_total: int | None
    max_uses_per_user: int | None
    applicable_category_ids: list[str]
    applicable_product_ids: list[str]
    stacks_with_automatic: bool
    status: CouponStatus
    created_at: datetime
    updated_at: datetime


class CouponCreateIn(_Strict):
    code: str = Field(min_length=2, max_length=80, pattern=r"^[A-Za-z0-9-]+$")
    type: CouponType
    value: int = Field(gt=0)
    min_order_cents: int = Field(ge=0, default=0)
    valid_from: datetime | None = None
    valid_until: datetime | None = None
    max_uses_total: int | None = Field(default=None, gt=0)
    max_uses_per_user: int | None = Field(default=None, gt=0)
    applicable_category_ids: list[str] = Field(default_factory=list)
    applicable_product_ids: list[str] = Field(default_factory=list)
    stacks_with_automatic: bool = False
    status: CouponStatus = "active"


class CouponUpdateIn(_Strict):
    code: str | None = Field(default=None, min_length=2, max_length=80, pattern=r"^[A-Za-z0-9-]+$")
    type: CouponType | None = None
    value: int | None = Field(default=None, gt=0)
    min_order_cents: int | None = Field(default=None, ge=0)
    valid_from: datetime | None = None
    valid_until: datetime | None = None
    max_uses_total: int | None = Field(default=None, gt=0)
    max_uses_per_user: int | None = Field(default=None, gt=0)
    applicable_category_ids: list[str] | None = None
    applicable_product_ids: list[str] | None = None
    stacks_with_automatic: bool | None = None
    status: CouponStatus | None = None


class CouponAdminOut(_Strict):
    coupon: CouponAdmin


class CouponAdminListOut(_Strict):
    data: list[CouponAdmin]
