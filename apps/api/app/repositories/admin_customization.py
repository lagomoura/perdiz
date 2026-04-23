"""Admin repositories for customization_groups and customization_options."""

from __future__ import annotations

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.customization_group import CustomizationGroup
from app.models.customization_option import CustomizationOption

# --- Groups ------------------------------------------------------------------


async def list_groups(db: AsyncSession, product_id: str) -> list[CustomizationGroup]:
    rows = await db.execute(
        select(CustomizationGroup)
        .where(CustomizationGroup.product_id == product_id)
        .order_by(CustomizationGroup.sort_order.asc(), CustomizationGroup.name.asc())
    )
    return list(rows.scalars().all())


async def get_group(db: AsyncSession, group_id: str) -> CustomizationGroup | None:
    return await db.get(CustomizationGroup, group_id)


async def create_group(
    db: AsyncSession,
    *,
    product_id: str,
    name: str,
    type: str,
    required: bool,
    selection_mode: str,
    sort_order: int,
    metadata: dict,  # type: ignore[type-arg]
) -> CustomizationGroup:
    group = CustomizationGroup(
        product_id=product_id,
        name=name,
        type=type,
        required=required,
        selection_mode=selection_mode,
        sort_order=sort_order,
        group_metadata=metadata,
    )
    db.add(group)
    await db.flush()
    await db.refresh(group)
    return group


def apply_group_updates(group: CustomizationGroup, updates: dict) -> None:  # type: ignore[type-arg]
    for key, value in updates.items():
        # Pydantic exposes the group's metadata as "metadata"; the ORM
        # attribute is ``group_metadata`` (SQLAlchemy reserves ``metadata``).
        if key == "metadata":
            group.group_metadata = value
        else:
            setattr(group, key, value)


async def delete_group(db: AsyncSession, group: CustomizationGroup) -> None:
    await db.delete(group)
    await db.flush()


# --- Options -----------------------------------------------------------------


async def list_options(db: AsyncSession, group_id: str) -> list[CustomizationOption]:
    rows = await db.execute(
        select(CustomizationOption)
        .where(CustomizationOption.group_id == group_id)
        .order_by(CustomizationOption.sort_order.asc(), CustomizationOption.label.asc())
    )
    return list(rows.scalars().all())


async def get_option(db: AsyncSession, option_id: str) -> CustomizationOption | None:
    return await db.get(CustomizationOption, option_id)


async def create_option(
    db: AsyncSession,
    *,
    group_id: str,
    label: str,
    price_modifier_cents: int,
    is_default: bool,
    is_available: bool,
    sort_order: int,
    metadata: dict,  # type: ignore[type-arg]
) -> CustomizationOption:
    option = CustomizationOption(
        group_id=group_id,
        label=label,
        price_modifier_cents=price_modifier_cents,
        is_default=is_default,
        is_available=is_available,
        sort_order=sort_order,
        option_metadata=metadata,
    )
    db.add(option)
    await db.flush()
    await db.refresh(option)
    return option


def apply_option_updates(option: CustomizationOption, updates: dict) -> None:  # type: ignore[type-arg]
    for key, value in updates.items():
        if key == "metadata":
            option.option_metadata = value
        else:
            setattr(option, key, value)


async def delete_option(db: AsyncSession, option: CustomizationOption) -> None:
    await db.delete(option)
    await db.flush()


async def clear_default_for_group(
    db: AsyncSession, *, group_id: str, except_option_id: str | None = None
) -> None:
    """Set ``is_default=False`` on every option of ``group_id`` except the
    one identified by ``except_option_id`` (if given)."""
    stmt = update(CustomizationOption).where(CustomizationOption.group_id == group_id)
    if except_option_id is not None:
        stmt = stmt.where(CustomizationOption.id != except_option_id)
    stmt = stmt.values(is_default=False)
    await db.execute(stmt)
