"""Admin coupon CRUD with audit logging."""

from __future__ import annotations

from typing import Any

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions import NotFoundError, ResourceConflict, ValidationError
from app.models.coupon import Coupon
from app.models.user import User
from app.repositories import coupons as repo
from app.services import audit


def _validate_percentage(type_: str, value: int) -> None:
    if type_ == "percentage" and not 1 <= value <= 100:
        raise ValidationError(
            "Un descuento porcentual debe estar entre 1 y 100.",
            details={"field": "value"},
        )


def _validate_window(valid_from, valid_until) -> None:  # type: ignore[no-untyped-def]
    if valid_from and valid_until and valid_until <= valid_from:
        raise ValidationError(
            "valid_until debe ser posterior a valid_from.",
            details={"field": "valid_until"},
        )


async def list_coupons(db: AsyncSession, *, status: str | None = None) -> list[Coupon]:
    return await repo.list_all(db, status=status)


async def get_coupon(db: AsyncSession, coupon_id: str) -> Coupon:
    coupon = await repo.get_by_id(db, coupon_id)
    if coupon is None:
        raise NotFoundError("Cupón no encontrado.")
    return coupon


async def create_coupon(db: AsyncSession, *, actor: User, payload: dict[str, Any]) -> Coupon:
    _validate_percentage(payload["type"], payload["value"])
    _validate_window(payload.get("valid_from"), payload.get("valid_until"))
    try:
        coupon = await repo.create(db, **payload)
    except IntegrityError as e:
        raise ResourceConflict(
            "Ya existe un cupón con ese código.", details={"field": "code"}
        ) from e

    await audit.log_mutation(
        db,
        actor=actor,
        action="coupon.create",
        entity_type="coupon",
        entity_id=coupon.id,
        before=None,
        after=audit.snapshot(coupon),
    )
    await db.commit()
    return coupon


async def update_coupon(
    db: AsyncSession, *, actor: User, coupon_id: str, updates: dict[str, Any]
) -> Coupon:
    coupon = await repo.get_by_id(db, coupon_id)
    if coupon is None:
        raise NotFoundError("Cupón no encontrado.")
    new_type = updates.get("type", coupon.type)
    new_value = updates.get("value", coupon.value)
    _validate_percentage(new_type, new_value)
    _validate_window(
        updates.get("valid_from", coupon.valid_from),
        updates.get("valid_until", coupon.valid_until),
    )
    before = audit.snapshot(coupon)
    repo.apply_updates(coupon, updates)
    try:
        await db.flush()
    except IntegrityError as e:
        raise ResourceConflict(
            "Ya existe un cupón con ese código.", details={"field": "code"}
        ) from e
    await db.refresh(coupon)

    await audit.log_mutation(
        db,
        actor=actor,
        action="coupon.update",
        entity_type="coupon",
        entity_id=coupon.id,
        before=before,
        after=audit.snapshot(coupon),
    )
    await db.commit()
    return coupon


async def delete_coupon(db: AsyncSession, *, actor: User, coupon_id: str) -> None:
    coupon = await repo.get_by_id(db, coupon_id)
    if coupon is None:
        raise NotFoundError("Cupón no encontrado.")
    before = audit.snapshot(coupon)
    await repo.delete(db, coupon)
    await audit.log_mutation(
        db,
        actor=actor,
        action="coupon.delete",
        entity_type="coupon",
        entity_id=coupon_id,
        before=before,
        after=None,
    )
    await db.commit()
