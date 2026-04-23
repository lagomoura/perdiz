"""Admin customization endpoints (groups + options)."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Response

from app.api.deps import DbSession, require_role
from app.models.user import User
from app.schemas.admin_customization import (
    CustomizationGroupAdmin,
    CustomizationGroupCreateIn,
    CustomizationGroupListOut,
    CustomizationGroupOut,
    CustomizationGroupUpdateIn,
    CustomizationOptionAdmin,
    CustomizationOptionCreateIn,
    CustomizationOptionListOut,
    CustomizationOptionOut,
    CustomizationOptionUpdateIn,
)
from app.services.catalog import admin_customization as service

router = APIRouter(
    prefix="/admin",
    tags=["admin-catalog"],
    dependencies=[Depends(require_role("admin"))],
)


def _group_to_dto(g) -> CustomizationGroupAdmin:  # type: ignore[no-untyped-def]
    return CustomizationGroupAdmin(
        id=g.id,
        product_id=g.product_id,
        name=g.name,
        type=g.type,
        required=g.required,
        selection_mode=g.selection_mode,
        sort_order=g.sort_order,
        metadata=g.group_metadata,
        created_at=g.created_at,
        updated_at=g.updated_at,
    )


def _option_to_dto(o) -> CustomizationOptionAdmin:  # type: ignore[no-untyped-def]
    return CustomizationOptionAdmin(
        id=o.id,
        group_id=o.group_id,
        label=o.label,
        price_modifier_cents=o.price_modifier_cents,
        is_default=o.is_default,
        is_available=o.is_available,
        sort_order=o.sort_order,
        metadata=o.option_metadata,
        created_at=o.created_at,
        updated_at=o.updated_at,
    )


# --- Groups ------------------------------------------------------------------


@router.get(
    "/products/{product_id}/customization-groups",
    response_model=CustomizationGroupListOut,
)
async def list_groups(product_id: str, db: DbSession) -> CustomizationGroupListOut:
    groups = await service.list_groups(db, product_id)
    return CustomizationGroupListOut(data=[_group_to_dto(g) for g in groups])


@router.post(
    "/products/{product_id}/customization-groups",
    response_model=CustomizationGroupOut,
    status_code=201,
)
async def create_group(
    product_id: str,
    payload: CustomizationGroupCreateIn,
    db: DbSession,
    actor: Annotated[User, Depends(require_role("admin"))],
) -> CustomizationGroupOut:
    group = await service.create_group(
        db, actor=actor, product_id=product_id, payload=payload.model_dump()
    )
    return CustomizationGroupOut(group=_group_to_dto(group))


@router.get(
    "/products/{product_id}/customization-groups/{group_id}",
    response_model=CustomizationGroupOut,
)
async def get_group(product_id: str, group_id: str, db: DbSession) -> CustomizationGroupOut:
    group = await service.get_group(db, product_id=product_id, group_id=group_id)
    return CustomizationGroupOut(group=_group_to_dto(group))


@router.patch(
    "/products/{product_id}/customization-groups/{group_id}",
    response_model=CustomizationGroupOut,
)
async def update_group(
    product_id: str,
    group_id: str,
    payload: CustomizationGroupUpdateIn,
    db: DbSession,
    actor: Annotated[User, Depends(require_role("admin"))],
) -> CustomizationGroupOut:
    updates = payload.model_dump(exclude_unset=True)
    group = await service.update_group(
        db,
        actor=actor,
        product_id=product_id,
        group_id=group_id,
        updates=updates,
    )
    return CustomizationGroupOut(group=_group_to_dto(group))


@router.delete("/products/{product_id}/customization-groups/{group_id}", status_code=204)
async def delete_group(
    product_id: str,
    group_id: str,
    db: DbSession,
    actor: Annotated[User, Depends(require_role("admin"))],
) -> Response:
    await service.delete_group(db, actor=actor, product_id=product_id, group_id=group_id)
    return Response(status_code=204)


# --- Options -----------------------------------------------------------------


@router.get(
    "/customization-groups/{group_id}/options",
    response_model=CustomizationOptionListOut,
)
async def list_options(group_id: str, db: DbSession) -> CustomizationOptionListOut:
    options = await service.list_options(db, group_id)
    return CustomizationOptionListOut(data=[_option_to_dto(o) for o in options])


@router.post(
    "/customization-groups/{group_id}/options",
    response_model=CustomizationOptionOut,
    status_code=201,
)
async def create_option(
    group_id: str,
    payload: CustomizationOptionCreateIn,
    db: DbSession,
    actor: Annotated[User, Depends(require_role("admin"))],
) -> CustomizationOptionOut:
    option = await service.create_option(
        db, actor=actor, group_id=group_id, payload=payload.model_dump()
    )
    return CustomizationOptionOut(option=_option_to_dto(option))


@router.patch(
    "/customization-groups/{group_id}/options/{option_id}",
    response_model=CustomizationOptionOut,
)
async def update_option(
    group_id: str,
    option_id: str,
    payload: CustomizationOptionUpdateIn,
    db: DbSession,
    actor: Annotated[User, Depends(require_role("admin"))],
) -> CustomizationOptionOut:
    updates = payload.model_dump(exclude_unset=True)
    option = await service.update_option(
        db,
        actor=actor,
        group_id=group_id,
        option_id=option_id,
        updates=updates,
    )
    return CustomizationOptionOut(option=_option_to_dto(option))


@router.delete("/customization-groups/{group_id}/options/{option_id}", status_code=204)
async def delete_option(
    group_id: str,
    option_id: str,
    db: DbSession,
    actor: Annotated[User, Depends(require_role("admin"))],
) -> Response:
    await service.delete_option(db, actor=actor, group_id=group_id, option_id=option_id)
    return Response(status_code=204)
