"""Admin service for customization groups + options.

Cross-field rule: a group with ``selection_mode='single'`` can have at most
one option with ``is_default=True``. The service enforces this whenever an
option is created/updated and auto-clears any other defaults in the group.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions import NotFoundError
from app.models.customization_group import CustomizationGroup
from app.models.customization_option import CustomizationOption
from app.models.user import User
from app.repositories import admin_customization as repo
from app.repositories import admin_products as prod_repo
from app.services import audit

# --- Groups ------------------------------------------------------------------


async def list_groups(db: AsyncSession, product_id: str) -> list[CustomizationGroup]:
    if await prod_repo.get_by_id(db, product_id) is None:
        raise NotFoundError("Producto no encontrado.")
    return await repo.list_groups(db, product_id)


async def create_group(
    db: AsyncSession,
    *,
    actor: User,
    product_id: str,
    payload: dict[str, Any],
) -> CustomizationGroup:
    if await prod_repo.get_by_id(db, product_id) is None:
        raise NotFoundError("Producto no encontrado.")
    group = await repo.create_group(
        db,
        product_id=product_id,
        name=payload["name"],
        type=payload["type"],
        required=payload["required"],
        selection_mode=payload["selection_mode"],
        sort_order=payload["sort_order"],
        metadata=payload["metadata"],
    )
    await audit.log_mutation(
        db,
        actor=actor,
        action="customization_group.create",
        entity_type="customization_group",
        entity_id=group.id,
        before=None,
        after=audit.snapshot(group),
    )
    await db.commit()
    return group


async def get_group(db: AsyncSession, *, product_id: str, group_id: str) -> CustomizationGroup:
    group = await repo.get_group(db, group_id)
    if group is None or group.product_id != product_id:
        raise NotFoundError("Grupo de personalización no encontrado.")
    return group


async def update_group(
    db: AsyncSession,
    *,
    actor: User,
    product_id: str,
    group_id: str,
    updates: dict[str, Any],
) -> CustomizationGroup:
    group = await get_group(db, product_id=product_id, group_id=group_id)
    before = audit.snapshot(group)
    repo.apply_group_updates(group, updates)
    await db.flush()
    await db.refresh(group)
    await audit.log_mutation(
        db,
        actor=actor,
        action="customization_group.update",
        entity_type="customization_group",
        entity_id=group.id,
        before=before,
        after=audit.snapshot(group),
    )
    await db.commit()
    return group


async def delete_group(db: AsyncSession, *, actor: User, product_id: str, group_id: str) -> None:
    group = await get_group(db, product_id=product_id, group_id=group_id)
    before = audit.snapshot(group)
    await repo.delete_group(db, group)
    await audit.log_mutation(
        db,
        actor=actor,
        action="customization_group.delete",
        entity_type="customization_group",
        entity_id=group_id,
        before=before,
        after=None,
    )
    await db.commit()


# --- Options -----------------------------------------------------------------


async def list_options(db: AsyncSession, group_id: str) -> list[CustomizationOption]:
    if await repo.get_group(db, group_id) is None:
        raise NotFoundError("Grupo de personalización no encontrado.")
    return await repo.list_options(db, group_id)


async def create_option(
    db: AsyncSession,
    *,
    actor: User,
    group_id: str,
    payload: dict[str, Any],
) -> CustomizationOption:
    group = await repo.get_group(db, group_id)
    if group is None:
        raise NotFoundError("Grupo de personalización no encontrado.")

    if payload["is_default"] and group.selection_mode == "single":
        # Clear any existing default in the same single-selection group.
        await repo.clear_default_for_group(db, group_id=group_id)

    option = await repo.create_option(
        db,
        group_id=group_id,
        label=payload["label"],
        price_modifier_cents=payload["price_modifier_cents"],
        is_default=payload["is_default"],
        is_available=payload["is_available"],
        sort_order=payload["sort_order"],
        metadata=payload["metadata"],
    )
    await audit.log_mutation(
        db,
        actor=actor,
        action="customization_option.create",
        entity_type="customization_option",
        entity_id=option.id,
        before=None,
        after=audit.snapshot(option),
    )
    await db.commit()
    return option


async def update_option(
    db: AsyncSession,
    *,
    actor: User,
    group_id: str,
    option_id: str,
    updates: dict[str, Any],
) -> CustomizationOption:
    option = await repo.get_option(db, option_id)
    if option is None or option.group_id != group_id:
        raise NotFoundError("Opción de personalización no encontrada.")

    before = audit.snapshot(option)
    repo.apply_option_updates(option, updates)
    await db.flush()

    # If the caller is flipping this option to default in a single-selection
    # group, clear any other defaults in the same group.
    if updates.get("is_default") is True:
        group = await repo.get_group(db, group_id)
        if group is not None and group.selection_mode == "single":
            await repo.clear_default_for_group(db, group_id=group_id, except_option_id=option.id)
            await db.flush()

    await db.refresh(option)
    await audit.log_mutation(
        db,
        actor=actor,
        action="customization_option.update",
        entity_type="customization_option",
        entity_id=option.id,
        before=before,
        after=audit.snapshot(option),
    )
    await db.commit()
    return option


async def delete_option(db: AsyncSession, *, actor: User, group_id: str, option_id: str) -> None:
    option = await repo.get_option(db, option_id)
    if option is None or option.group_id != group_id:
        raise NotFoundError("Opción de personalización no encontrada.")
    before = audit.snapshot(option)
    await repo.delete_option(db, option)
    await audit.log_mutation(
        db,
        actor=actor,
        action="customization_option.delete",
        entity_type="customization_option",
        entity_id=option_id,
        before=before,
        after=None,
    )
    await db.commit()
