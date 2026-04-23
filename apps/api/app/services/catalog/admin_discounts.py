"""Admin service for volume_discounts and automatic_discounts."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions import NotFoundError, ValidationError
from app.models.automatic_discount import AutomaticDiscount
from app.models.user import User
from app.models.volume_discount import VolumeDiscount
from app.repositories import admin_categories as cat_repo
from app.repositories import admin_discounts as repo
from app.repositories import admin_products as prod_repo
from app.services import audit


def _validate_percentage(type_: str, value: int) -> None:
    if type_ == "percentage" and not 1 <= value <= 100:
        raise ValidationError(
            "Un descuento porcentual debe estar entre 1 y 100.",
            details={"field": "value"},
        )


def _validate_time_window(valid_from: datetime | None, valid_until: datetime | None) -> None:
    if valid_from and valid_until and valid_until <= valid_from:
        raise ValidationError(
            "valid_until debe ser posterior a valid_from.",
            details={"field": "valid_until"},
        )


# --- Volume discounts --------------------------------------------------------


async def list_volume_for_product(db: AsyncSession, product_id: str) -> list[VolumeDiscount]:
    if await prod_repo.get_by_id(db, product_id) is None:
        raise NotFoundError("Producto no encontrado.")
    return await repo.list_volume_for_product(db, product_id)


async def create_volume_discount(
    db: AsyncSession,
    *,
    actor: User,
    product_id: str,
    min_quantity: int,
    type: str,
    value: int,
) -> VolumeDiscount:
    if await prod_repo.get_by_id(db, product_id) is None:
        raise NotFoundError("Producto no encontrado.")
    _validate_percentage(type, value)
    discount = await repo.create_volume(
        db,
        product_id=product_id,
        min_quantity=min_quantity,
        type=type,
        value=value,
    )
    await audit.log_mutation(
        db,
        actor=actor,
        action="volume_discount.create",
        entity_type="volume_discount",
        entity_id=discount.id,
        before=None,
        after=audit.snapshot(discount),
    )
    await db.commit()
    return discount


async def delete_volume_discount(
    db: AsyncSession, *, actor: User, product_id: str, discount_id: str
) -> None:
    discount = await repo.get_volume(db, discount_id)
    if discount is None or discount.product_id != product_id:
        raise NotFoundError("Descuento por volumen no encontrado.")
    before = audit.snapshot(discount)
    await repo.delete_volume(db, discount)
    await audit.log_mutation(
        db,
        actor=actor,
        action="volume_discount.delete",
        entity_type="volume_discount",
        entity_id=discount_id,
        before=before,
        after=None,
    )
    await db.commit()


# --- Automatic discounts -----------------------------------------------------


async def _validate_target(db: AsyncSession, *, scope: str, target_id: str) -> None:
    if scope == "category" and await cat_repo.get_by_id(db, target_id) is None:
        raise ValidationError("La categoría target no existe.", details={"field": "target_id"})
    if scope == "product" and await prod_repo.get_by_id(db, target_id) is None:
        raise ValidationError("El producto target no existe.", details={"field": "target_id"})


async def list_automatic(
    db: AsyncSession, *, status: str | None = None, scope: str | None = None
) -> list[AutomaticDiscount]:
    return await repo.list_automatic(db, status=status, scope=scope)


async def create_automatic(
    db: AsyncSession, *, actor: User, payload: dict[str, Any]
) -> AutomaticDiscount:
    _validate_percentage(payload["type"], payload["value"])
    _validate_time_window(payload.get("valid_from"), payload.get("valid_until"))
    await _validate_target(db, scope=payload["scope"], target_id=payload["target_id"])

    discount = await repo.create_automatic(db, **payload)
    await audit.log_mutation(
        db,
        actor=actor,
        action="automatic_discount.create",
        entity_type="automatic_discount",
        entity_id=discount.id,
        before=None,
        after=audit.snapshot(discount),
    )
    await db.commit()
    return discount


async def get_automatic(db: AsyncSession, discount_id: str) -> AutomaticDiscount:
    discount = await repo.get_automatic(db, discount_id)
    if discount is None:
        raise NotFoundError("Descuento automático no encontrado.")
    return discount


async def update_automatic(
    db: AsyncSession,
    *,
    actor: User,
    discount_id: str,
    updates: dict[str, Any],
) -> AutomaticDiscount:
    discount = await repo.get_automatic(db, discount_id)
    if discount is None:
        raise NotFoundError("Descuento automático no encontrado.")

    new_type = updates.get("type", discount.type)
    new_value = updates.get("value", discount.value)
    _validate_percentage(new_type, new_value)
    _validate_time_window(
        updates.get("valid_from", discount.valid_from),
        updates.get("valid_until", discount.valid_until),
    )
    if "scope" in updates or "target_id" in updates:
        await _validate_target(
            db,
            scope=updates.get("scope", discount.scope),
            target_id=updates.get("target_id", discount.target_id),
        )

    before = audit.snapshot(discount)
    repo.apply_automatic_updates(discount, updates)
    await db.flush()
    await db.refresh(discount)
    await audit.log_mutation(
        db,
        actor=actor,
        action="automatic_discount.update",
        entity_type="automatic_discount",
        entity_id=discount.id,
        before=before,
        after=audit.snapshot(discount),
    )
    await db.commit()
    return discount


async def delete_automatic(db: AsyncSession, *, actor: User, discount_id: str) -> None:
    discount = await repo.get_automatic(db, discount_id)
    if discount is None:
        raise NotFoundError("Descuento automático no encontrado.")
    before = audit.snapshot(discount)
    await repo.delete_automatic(db, discount)
    await audit.log_mutation(
        db,
        actor=actor,
        action="automatic_discount.delete",
        entity_type="automatic_discount",
        entity_id=discount_id,
        before=before,
        after=None,
    )
    await db.commit()
