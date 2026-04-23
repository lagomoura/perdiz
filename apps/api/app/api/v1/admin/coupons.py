"""Admin coupons CRUD."""

from __future__ import annotations

from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query, Response

from app.api.deps import DbSession, require_role
from app.models.user import User
from app.schemas.admin_coupons import (
    CouponAdmin,
    CouponAdminListOut,
    CouponAdminOut,
    CouponCreateIn,
    CouponUpdateIn,
)
from app.services.cart import coupons_admin as service

router = APIRouter(
    prefix="/admin/coupons",
    tags=["admin-catalog"],
    dependencies=[Depends(require_role("admin"))],
)


def _serialize(c) -> CouponAdmin:  # type: ignore[no-untyped-def]
    return CouponAdmin(
        id=c.id,
        code=c.code,
        type=c.type,
        value=c.value,
        min_order_cents=c.min_order_cents,
        valid_from=c.valid_from,
        valid_until=c.valid_until,
        max_uses_total=c.max_uses_total,
        max_uses_per_user=c.max_uses_per_user,
        applicable_category_ids=list(c.applicable_category_ids or []),
        applicable_product_ids=list(c.applicable_product_ids or []),
        stacks_with_automatic=c.stacks_with_automatic,
        status=c.status,
        created_at=c.created_at,
        updated_at=c.updated_at,
    )


@router.get("", response_model=CouponAdminListOut)
async def list_coupons(
    db: DbSession,
    status: Annotated[Literal["active", "disabled"] | None, Query()] = None,
) -> CouponAdminListOut:
    rows = await service.list_coupons(db, status=status)
    return CouponAdminListOut(data=[_serialize(c) for c in rows])


@router.post("", response_model=CouponAdminOut, status_code=201)
async def create_coupon(
    payload: CouponCreateIn,
    db: DbSession,
    actor: Annotated[User, Depends(require_role("admin"))],
) -> CouponAdminOut:
    coupon = await service.create_coupon(db, actor=actor, payload=payload.model_dump())
    return CouponAdminOut(coupon=_serialize(coupon))


@router.get("/{coupon_id}", response_model=CouponAdminOut)
async def get_coupon(coupon_id: str, db: DbSession) -> CouponAdminOut:
    coupon = await service.get_coupon(db, coupon_id)
    return CouponAdminOut(coupon=_serialize(coupon))


@router.patch("/{coupon_id}", response_model=CouponAdminOut)
async def update_coupon(
    coupon_id: str,
    payload: CouponUpdateIn,
    db: DbSession,
    actor: Annotated[User, Depends(require_role("admin"))],
) -> CouponAdminOut:
    updates = payload.model_dump(exclude_unset=True)
    coupon = await service.update_coupon(db, actor=actor, coupon_id=coupon_id, updates=updates)
    return CouponAdminOut(coupon=_serialize(coupon))


@router.delete("/{coupon_id}", status_code=204)
async def delete_coupon(
    coupon_id: str,
    db: DbSession,
    actor: Annotated[User, Depends(require_role("admin"))],
) -> Response:
    await service.delete_coupon(db, actor=actor, coupon_id=coupon_id)
    return Response(status_code=204)
