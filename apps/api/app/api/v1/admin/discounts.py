"""Admin discounts endpoints: volume + automatic."""

from __future__ import annotations

from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query, Response

from app.api.deps import DbSession, require_role
from app.models.user import User
from app.schemas.admin_customization import (
    AutomaticDiscountAdmin,
    AutomaticDiscountCreateIn,
    AutomaticDiscountListOut,
    AutomaticDiscountOut,
    AutomaticDiscountUpdateIn,
    VolumeDiscountAdmin,
    VolumeDiscountCreateIn,
    VolumeDiscountListOut,
    VolumeDiscountOut,
)
from app.services.catalog import admin_discounts as service

router = APIRouter(
    prefix="/admin",
    tags=["admin-catalog"],
    dependencies=[Depends(require_role("admin"))],
)


# --- Volume (per product, nested) -------------------------------------------


def _volume_to_dto(v) -> VolumeDiscountAdmin:  # type: ignore[no-untyped-def]
    return VolumeDiscountAdmin(
        id=v.id,
        product_id=v.product_id,
        min_quantity=v.min_quantity,
        type=v.type,
        value=v.value,
    )


@router.get("/products/{product_id}/volume-discounts", response_model=VolumeDiscountListOut)
async def list_volume(product_id: str, db: DbSession) -> VolumeDiscountListOut:
    rows = await service.list_volume_for_product(db, product_id)
    return VolumeDiscountListOut(data=[_volume_to_dto(v) for v in rows])


@router.post(
    "/products/{product_id}/volume-discounts",
    response_model=VolumeDiscountOut,
    status_code=201,
)
async def create_volume(
    product_id: str,
    payload: VolumeDiscountCreateIn,
    db: DbSession,
    actor: Annotated[User, Depends(require_role("admin"))],
) -> VolumeDiscountOut:
    discount = await service.create_volume_discount(
        db,
        actor=actor,
        product_id=product_id,
        min_quantity=payload.min_quantity,
        type=payload.type,
        value=payload.value,
    )
    return VolumeDiscountOut(discount=_volume_to_dto(discount))


@router.delete("/products/{product_id}/volume-discounts/{discount_id}", status_code=204)
async def delete_volume(
    product_id: str,
    discount_id: str,
    db: DbSession,
    actor: Annotated[User, Depends(require_role("admin"))],
) -> Response:
    await service.delete_volume_discount(
        db, actor=actor, product_id=product_id, discount_id=discount_id
    )
    return Response(status_code=204)


# --- Automatic (global, top-level) ------------------------------------------


def _auto_to_dto(d) -> AutomaticDiscountAdmin:  # type: ignore[no-untyped-def]
    return AutomaticDiscountAdmin(
        id=d.id,
        name=d.name,
        type=d.type,
        value=d.value,
        scope=d.scope,
        target_id=d.target_id,
        valid_from=d.valid_from,
        valid_until=d.valid_until,
        status=d.status,
        created_at=d.created_at,
        updated_at=d.updated_at,
    )


@router.get("/discounts", response_model=AutomaticDiscountListOut)
async def list_automatic(
    db: DbSession,
    status: Annotated[Literal["active", "disabled"] | None, Query()] = None,
    scope: Annotated[Literal["category", "product"] | None, Query()] = None,
) -> AutomaticDiscountListOut:
    rows = await service.list_automatic(db, status=status, scope=scope)
    return AutomaticDiscountListOut(data=[_auto_to_dto(d) for d in rows])


@router.post("/discounts", response_model=AutomaticDiscountOut, status_code=201)
async def create_automatic(
    payload: AutomaticDiscountCreateIn,
    db: DbSession,
    actor: Annotated[User, Depends(require_role("admin"))],
) -> AutomaticDiscountOut:
    discount = await service.create_automatic(db, actor=actor, payload=payload.model_dump())
    return AutomaticDiscountOut(discount=_auto_to_dto(discount))


@router.get("/discounts/{discount_id}", response_model=AutomaticDiscountOut)
async def get_automatic(discount_id: str, db: DbSession) -> AutomaticDiscountOut:
    discount = await service.get_automatic(db, discount_id)
    return AutomaticDiscountOut(discount=_auto_to_dto(discount))


@router.patch("/discounts/{discount_id}", response_model=AutomaticDiscountOut)
async def update_automatic(
    discount_id: str,
    payload: AutomaticDiscountUpdateIn,
    db: DbSession,
    actor: Annotated[User, Depends(require_role("admin"))],
) -> AutomaticDiscountOut:
    updates = payload.model_dump(exclude_unset=True)
    discount = await service.update_automatic(
        db, actor=actor, discount_id=discount_id, updates=updates
    )
    return AutomaticDiscountOut(discount=_auto_to_dto(discount))


@router.delete("/discounts/{discount_id}", status_code=204)
async def delete_automatic(
    discount_id: str,
    db: DbSession,
    actor: Annotated[User, Depends(require_role("admin"))],
) -> Response:
    await service.delete_automatic(db, actor=actor, discount_id=discount_id)
    return Response(status_code=204)
