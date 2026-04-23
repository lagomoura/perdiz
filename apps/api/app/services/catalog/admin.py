"""Admin catalog orchestration: categories + products CRUD with auditing.

All mutations inside a service function are bracketed by ``audit.log_mutation``.
The repo writes + the audit write happen in the same transaction — a rollback
on the mutation rolls back the audit too, which keeps the log honest.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions import NotFoundError, ResourceConflict, ValidationError
from app.models.category import Category
from app.models.product import Product
from app.models.user import User
from app.repositories import admin_categories as cat_repo
from app.repositories import admin_products as prod_repo
from app.services import audit

# --- Categories --------------------------------------------------------------


async def list_categories(
    db: AsyncSession, *, status: str | None = None, include_deleted: bool = False
) -> list[Category]:
    return await cat_repo.list_all(db, status=status, include_deleted=include_deleted)


async def get_category(db: AsyncSession, category_id: str) -> Category:
    cat = await cat_repo.get_by_id(db, category_id)
    if cat is None:
        raise NotFoundError("Categoría no encontrada.")
    return cat


async def create_category(
    db: AsyncSession,
    *,
    actor: User,
    name: str,
    slug: str,
    parent_id: str | None,
    description: str | None,
    image_url: str | None,
    sort_order: int,
    status: str,
) -> Category:
    if parent_id and not await cat_repo.get_by_id(db, parent_id):
        raise ValidationError("La categoría padre no existe.", details={"field": "parent_id"})
    try:
        cat = await cat_repo.create(
            db,
            name=name,
            slug=slug,
            parent_id=parent_id,
            description=description,
            image_url=image_url,
            sort_order=sort_order,
            status=status,
        )
    except IntegrityError as e:
        raise ResourceConflict(
            "Ya existe una categoría con ese slug.", details={"field": "slug"}
        ) from e

    await audit.log_mutation(
        db,
        actor=actor,
        action="category.create",
        entity_type="category",
        entity_id=cat.id,
        before=None,
        after=audit.snapshot(cat),
    )
    await db.commit()
    return cat


async def update_category(
    db: AsyncSession, *, actor: User, category_id: str, updates: dict[str, Any]
) -> Category:
    cat = await cat_repo.get_by_id(db, category_id)
    if cat is None:
        raise NotFoundError("Categoría no encontrada.")
    if "parent_id" in updates and updates["parent_id"] is not None:
        if updates["parent_id"] == cat.id:
            raise ValidationError(
                "Una categoría no puede ser su propio padre.",
                details={"field": "parent_id"},
            )
        if not await cat_repo.get_by_id(db, updates["parent_id"]):
            raise ValidationError("La categoría padre no existe.", details={"field": "parent_id"})

    before = audit.snapshot(cat)
    cat_repo.apply_updates(cat, updates)
    try:
        await db.flush()
    except IntegrityError as e:
        raise ResourceConflict(
            "Ya existe una categoría con ese slug.", details={"field": "slug"}
        ) from e
    # Refresh so server-side onupdate columns (updated_at) are re-hydrated
    # before the post-mutation snapshot; without this the sync snapshot
    # triggers a lazy-load in an async context (MissingGreenlet).
    await db.refresh(cat)

    await audit.log_mutation(
        db,
        actor=actor,
        action="category.update",
        entity_type="category",
        entity_id=cat.id,
        before=before,
        after=audit.snapshot(cat),
    )
    await db.commit()
    return cat


async def delete_category(db: AsyncSession, *, actor: User, category_id: str) -> None:
    cat = await cat_repo.get_by_id(db, category_id)
    if cat is None:
        raise NotFoundError("Categoría no encontrada.")
    before = audit.snapshot(cat)
    await cat_repo.soft_delete(db, cat)
    await db.refresh(cat)
    await audit.log_mutation(
        db,
        actor=actor,
        action="category.delete",
        entity_type="category",
        entity_id=cat.id,
        before=before,
        after=audit.snapshot(cat),
    )
    await db.commit()


# --- Products ---------------------------------------------------------------


_VALID_STATUS_TRANSITIONS = {
    "draft": {"active", "archived"},
    "active": {"draft", "archived"},
    "archived": {"draft", "active"},
}


async def list_products(
    db: AsyncSession,
    *,
    status: str | None = None,
    category_id: str | None = None,
    include_deleted: bool = False,
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[Product], int]:
    return await prod_repo.list_all(
        db,
        status=status,
        category_id=category_id,
        include_deleted=include_deleted,
        limit=limit,
        offset=offset,
    )


async def get_product(db: AsyncSession, product_id: str) -> Product:
    product = await prod_repo.get_by_id(db, product_id)
    if product is None:
        raise NotFoundError("Producto no encontrado.")
    return product


def _validate_stock_mode(payload: dict[str, Any]) -> None:
    mode = payload.get("stock_mode")
    if mode == "stocked":
        if payload.get("stock_quantity") is None:
            raise ValidationError(
                "Un producto con stock requiere stock_quantity.",
                details={"field": "stock_quantity"},
            )
        if payload.get("lead_time_days") is not None:
            raise ValidationError(
                "Un producto con stock no lleva lead_time_days.",
                details={"field": "lead_time_days"},
            )
    elif mode == "print_on_demand":
        if payload.get("lead_time_days") is None:
            raise ValidationError(
                "Un producto print-on-demand requiere lead_time_days.",
                details={"field": "lead_time_days"},
            )
        if payload.get("stock_quantity") is not None:
            raise ValidationError(
                "Un producto print-on-demand no lleva stock_quantity.",
                details={"field": "stock_quantity"},
            )


async def create_product(db: AsyncSession, *, actor: User, payload: dict[str, Any]) -> Product:
    # Validate category exists and isn't deleted.
    if not await cat_repo.get_by_id(db, payload["category_id"]):
        raise ValidationError("La categoría no existe.", details={"field": "category_id"})
    _validate_stock_mode(payload)
    try:
        product = await prod_repo.create(db, **payload)
    except IntegrityError as e:
        message = str(getattr(e, "orig", e))
        if "uq_products_slug" in message:
            raise ResourceConflict(
                "Ya existe un producto con ese slug.", details={"field": "slug"}
            ) from e
        if "uq_products_sku" in message:
            raise ResourceConflict(
                "Ya existe un producto con ese SKU.", details={"field": "sku"}
            ) from e
        raise ResourceConflict("No se pudo crear el producto.") from e

    await audit.log_mutation(
        db,
        actor=actor,
        action="product.create",
        entity_type="product",
        entity_id=product.id,
        before=None,
        after=audit.snapshot(product),
    )
    await db.commit()
    return product


async def update_product(
    db: AsyncSession, *, actor: User, product_id: str, updates: dict[str, Any]
) -> Product:
    product = await prod_repo.get_by_id(db, product_id)
    if product is None:
        raise NotFoundError("Producto no encontrado.")

    if (
        "category_id" in updates
        and updates["category_id"] is not None
        and not await cat_repo.get_by_id(db, updates["category_id"])
    ):
        raise ValidationError("La categoría no existe.", details={"field": "category_id"})

    merged = {
        "stock_mode": updates.get("stock_mode", product.stock_mode),
        "stock_quantity": updates.get(
            "stock_quantity",
            product.stock_quantity if "stock_quantity" not in updates else None,
        ),
        "lead_time_days": updates.get(
            "lead_time_days",
            product.lead_time_days if "lead_time_days" not in updates else None,
        ),
    }
    if any(k in updates for k in ("stock_mode", "stock_quantity", "lead_time_days")):
        _validate_stock_mode(merged)

    before = audit.snapshot(product)
    prod_repo.apply_updates(product, updates)
    try:
        await db.flush()
    except IntegrityError as e:
        message = str(getattr(e, "orig", e))
        if "uq_products_slug" in message:
            raise ResourceConflict(
                "Ya existe un producto con ese slug.", details={"field": "slug"}
            ) from e
        if "uq_products_sku" in message:
            raise ResourceConflict(
                "Ya existe un producto con ese SKU.", details={"field": "sku"}
            ) from e
        raise ResourceConflict("No se pudo actualizar el producto.") from e
    await db.refresh(product)

    await audit.log_mutation(
        db,
        actor=actor,
        action="product.update",
        entity_type="product",
        entity_id=product.id,
        before=before,
        after=audit.snapshot(product),
    )
    await db.commit()
    return product


async def transition_product_status(
    db: AsyncSession, *, actor: User, product_id: str, to_status: str
) -> Product:
    product = await prod_repo.get_by_id(db, product_id)
    if product is None:
        raise NotFoundError("Producto no encontrado.")
    current = product.status
    if current == to_status:
        return product
    allowed = _VALID_STATUS_TRANSITIONS.get(current, set())
    if to_status not in allowed:
        raise ValidationError(
            f"Transición inválida: {current} → {to_status}.",
            details={"field": "status"},
        )
    before = audit.snapshot(product)
    product.status = to_status
    await db.flush()
    await db.refresh(product)
    await audit.log_mutation(
        db,
        actor=actor,
        action="product.status.transition",
        entity_type="product",
        entity_id=product.id,
        before=before,
        after=audit.snapshot(product),
    )
    await db.commit()
    return product


async def delete_product(db: AsyncSession, *, actor: User, product_id: str) -> None:
    product = await prod_repo.get_by_id(db, product_id)
    if product is None:
        raise NotFoundError("Producto no encontrado.")
    before = audit.snapshot(product)
    await prod_repo.soft_delete(db, product)
    await db.refresh(product)
    await audit.log_mutation(
        db,
        actor=actor,
        action="product.delete",
        entity_type="product",
        entity_id=product.id,
        before=before,
        after=audit.snapshot(product),
    )
    await db.commit()
