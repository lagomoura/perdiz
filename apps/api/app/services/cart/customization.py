"""Validate customization selections when adding/updating cart items.

Expands the raw selections from the client into a resolved form:
- ``option_ids`` list (sorted, stable — powers dedupe across cart items)
- ``option_id`` for types that have a single virtual option
- ``value`` for ENGRAVING_TEXT
- ``file_id`` for ENGRAVING_IMAGE / USER_FILE
- ``resolved_modifier_cents`` accumulated across all selected options

Raises ``ValidationError`` on any violation per the rules documented in
docs/product/customization-model.md.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions import ValidationError
from app.models.customization_group import CustomizationGroup
from app.models.customization_option import CustomizationOption
from app.models.media_file import MediaFile

_SELECTION_TYPES: frozenset[str] = frozenset({"COLOR", "MATERIAL", "SIZE"})
_TEXT_TYPES: frozenset[str] = frozenset({"ENGRAVING_TEXT"})
_FILE_IMAGE_TYPES: frozenset[str] = frozenset({"ENGRAVING_IMAGE"})
_FILE_MODEL_TYPES: frozenset[str] = frozenset({"USER_FILE"})


@dataclass(frozen=True)
class ResolvedCustomizations:
    selections: list[dict[str, Any]]
    resolved_modifier_cents: int


async def validate_and_resolve(
    db: AsyncSession,
    *,
    product_id: str,
    actor_id: str | None,
    raw_selections: list[dict[str, Any]],
) -> ResolvedCustomizations:
    """Main entry point. Returns the normalized selections + total modifier."""
    groups = await _fetch_groups(db, product_id)
    groups_by_id = {g.id: g for g in groups}

    # Index input selections by group_id for convenient lookup.
    sel_by_group: dict[str, dict[str, Any]] = {}
    for sel in raw_selections:
        if "group_id" not in sel:
            raise ValidationError(
                "Falta group_id en una selección.",
                details={"code": "CUSTOMIZATION_INVALID_OPTION"},
            )
        sel_by_group[sel["group_id"]] = sel

    # Reject selections pointing at groups that aren't on this product.
    for gid in sel_by_group:
        if gid not in groups_by_id:
            raise ValidationError(
                "Una selección hace referencia a un grupo que no existe.",
                details={"code": "CUSTOMIZATION_INVALID_OPTION"},
            )

    resolved_selections: list[dict[str, Any]] = []
    total_modifier = 0

    for group in groups:
        raw = sel_by_group.get(group.id)
        if raw is None:
            if group.required:
                raise ValidationError(
                    f"Falta seleccionar una opción en el grupo '{group.name}'.",
                    details={"code": "CUSTOMIZATION_REQUIRED_GROUP_MISSING"},
                )
            continue

        entry, delta = await _resolve_group(db, group=group, raw=raw, actor_id=actor_id)
        total_modifier += delta
        resolved_selections.append(entry)

    return ResolvedCustomizations(
        selections=resolved_selections, resolved_modifier_cents=total_modifier
    )


async def _fetch_groups(db: AsyncSession, product_id: str) -> list[CustomizationGroup]:
    rows = await db.execute(
        select(CustomizationGroup)
        .where(CustomizationGroup.product_id == product_id)
        .order_by(CustomizationGroup.sort_order.asc())
    )
    return list(rows.scalars().all())


async def _resolve_group(
    db: AsyncSession,
    *,
    group: CustomizationGroup,
    raw: dict[str, Any],
    actor_id: str | None,
) -> tuple[dict[str, Any], int]:
    if group.type in _SELECTION_TYPES:
        return await _resolve_selection_group(db, group=group, raw=raw)
    if group.type in _TEXT_TYPES:
        return await _resolve_text_group(db, group=group, raw=raw)
    if group.type in _FILE_IMAGE_TYPES | _FILE_MODEL_TYPES:
        return await _resolve_file_group(db, group=group, raw=raw, actor_id=actor_id)
    raise ValidationError(
        f"Tipo de personalización no soportado: {group.type}.",
        details={"code": "CUSTOMIZATION_INVALID_OPTION"},
    )


async def _resolve_selection_group(
    db: AsyncSession, *, group: CustomizationGroup, raw: dict[str, Any]
) -> tuple[dict[str, Any], int]:
    option_ids = raw.get("option_ids") or []
    if not option_ids:
        raise ValidationError(
            f"Falta seleccionar una opción en '{group.name}'.",
            details={"code": "CUSTOMIZATION_INVALID_OPTION"},
        )
    if group.selection_mode == "single" and len(option_ids) != 1:
        raise ValidationError(
            f"'{group.name}' acepta una sola opción.",
            details={"code": "CUSTOMIZATION_INVALID_OPTION"},
        )

    options = await _fetch_options(db, group.id, option_ids)
    if len(options) != len(option_ids):
        raise ValidationError(
            "Una opción seleccionada no existe en el grupo.",
            details={"code": "CUSTOMIZATION_INVALID_OPTION"},
        )

    for opt in options:
        if not opt.is_available:
            raise ValidationError(
                f"La opción '{opt.label}' no está disponible.",
                details={"code": "CUSTOMIZATION_INVALID_OPTION"},
            )

    modifier = sum(opt.price_modifier_cents for opt in options)
    return (
        {
            "group_id": group.id,
            "type": group.type,
            "option_ids": sorted(option_ids),
        },
        modifier,
    )


async def _resolve_text_group(
    db: AsyncSession, *, group: CustomizationGroup, raw: dict[str, Any]
) -> tuple[dict[str, Any], int]:
    value = raw.get("value")
    if not isinstance(value, str):
        raise ValidationError(
            f"'{group.name}' requiere un texto.",
            details={"code": "CUSTOMIZATION_INVALID_OPTION"},
        )
    meta = group.group_metadata or {}
    min_len = int(meta.get("min_length", 1))
    max_len = int(meta.get("max_length", 80))
    if not min_len <= len(value) <= max_len:
        raise ValidationError(
            f"El texto de '{group.name}' debe tener entre {min_len} y {max_len} caracteres.",
            details={"code": "CUSTOMIZATION_INVALID_OPTION"},
        )
    charset = meta.get("allowed_charset")
    if charset == "alphanumeric_spaces" and not re.fullmatch(r"[\w\sáéíóúüñÁÉÍÓÚÜÑ]+", value):
        raise ValidationError(
            f"El texto de '{group.name}' solo puede contener letras, números y espacios.",
            details={"code": "CUSTOMIZATION_INVALID_OPTION"},
        )

    virtual = await _fetch_single_virtual_option(db, group.id)
    modifier = virtual.price_modifier_cents if virtual else 0
    return (
        {
            "group_id": group.id,
            "type": group.type,
            "value": value,
            "option_id": virtual.id if virtual else None,
        },
        modifier,
    )


async def _resolve_file_group(
    db: AsyncSession,
    *,
    group: CustomizationGroup,
    raw: dict[str, Any],
    actor_id: str | None,
) -> tuple[dict[str, Any], int]:
    file_id = raw.get("file_id")
    if not isinstance(file_id, str):
        raise ValidationError(
            f"'{group.name}' requiere subir un archivo.",
            details={"code": "CUSTOMIZATION_INVALID_OPTION"},
        )
    media = await db.get(MediaFile, file_id)
    if media is None or media.deleted_at is not None:
        raise ValidationError(
            "El archivo referenciado no existe.",
            details={"code": "CUSTOMIZATION_INVALID_OPTION"},
        )
    if media.owner_user_id != actor_id:
        raise ValidationError(
            "El archivo no pertenece al usuario.",
            details={"code": "CUSTOMIZATION_INVALID_OPTION"},
        )
    expected_kind = "user_upload_image" if group.type == "ENGRAVING_IMAGE" else "user_upload_model"
    if media.kind != expected_kind:
        raise ValidationError(
            f"El archivo debe ser de tipo {expected_kind}.",
            details={"code": "CUSTOMIZATION_INVALID_OPTION"},
        )
    # Respect declared max size per group metadata.
    max_mb = (group.group_metadata or {}).get("max_size_mb")
    if max_mb is not None and media.size_bytes > int(max_mb) * 1024 * 1024:
        raise ValidationError(
            f"El archivo supera los {max_mb} MB permitidos.",
            details={"code": "CUSTOMIZATION_FILE_TOO_LARGE"},
        )

    virtual = await _fetch_single_virtual_option(db, group.id)
    modifier = virtual.price_modifier_cents if virtual else 0
    return (
        {
            "group_id": group.id,
            "type": group.type,
            "file_id": file_id,
            "option_id": virtual.id if virtual else None,
        },
        modifier,
    )


async def _fetch_options(
    db: AsyncSession, group_id: str, option_ids: list[str]
) -> list[CustomizationOption]:
    rows = await db.execute(
        select(CustomizationOption).where(
            CustomizationOption.group_id == group_id,
            CustomizationOption.id.in_(option_ids),
        )
    )
    return list(rows.scalars().all())


async def _fetch_single_virtual_option(
    db: AsyncSession, group_id: str
) -> CustomizationOption | None:
    rows = await db.execute(
        select(CustomizationOption).where(CustomizationOption.group_id == group_id).limit(1)
    )
    return rows.scalars().first()


def selections_fingerprint(selections: list[dict[str, Any]]) -> str:
    """Canonical string for dedupe. Two items with the same product and
    fingerprint are collapsed (quantities summed).
    """
    normalized = []
    for sel in sorted(selections, key=lambda s: s.get("group_id", "")):
        clean = {
            k: v
            for k, v in sel.items()
            if k in {"group_id", "option_ids", "option_id", "value", "file_id"}
        }
        normalized.append(clean)
    return json.dumps(normalized, sort_keys=True, separators=(",", ":"))
