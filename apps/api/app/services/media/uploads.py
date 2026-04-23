"""Admin upload orchestration: presign + commit."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Literal

from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions import ValidationError
from app.models.media_file import MediaFile
from app.models.user import User
from app.services import audit
from app.services.media import queue as media_queue
from app.services.media import r2_client, validators
from app.utils.ulid import new_ulid

# Match everything that's not [a-zA-Z0-9._-] to keep the storage key safe.
_UNSAFE_FILENAME_CHARS = re.compile(r"[^A-Za-z0-9._-]+")

ADMIN_KINDS: frozenset[str] = frozenset({"image", "model_stl"})


@dataclass(frozen=True)
class PresignedUpload:
    storage_key: str
    url: str
    method: Literal["PUT"]
    headers: dict[str, str]
    expires_at: datetime


def _sanitize_filename(name: str) -> str:
    # Strip path components that some browsers send.
    tail = name.rsplit("/", 1)[-1].rsplit("\\", 1)[-1]
    cleaned = _UNSAFE_FILENAME_CHARS.sub("-", tail).strip("-") or "file"
    # Truncate to keep the key manageable.
    return cleaned[:120]


def _kind_prefix(kind: str) -> str:
    return {
        "image": "images",
        "model_stl": "models/stl",
    }[kind]


def _max_size_for_kind(kind: str) -> int:
    return {
        "image": validators.MAX_IMAGE_BYTES,
        "model_stl": validators.MAX_STL_BYTES,
    }[kind]


async def presign(
    *,
    kind: str,
    mime_type: str,
    size_bytes: int,
    filename: str,
) -> PresignedUpload:
    if kind not in ADMIN_KINDS:
        raise ValidationError("Tipo de upload no soportado.", details={"field": "kind"})
    limit = _max_size_for_kind(kind)
    if size_bytes <= 0 or size_bytes > limit:
        raise ValidationError(
            f"El archivo supera el tamaño máximo permitido para {kind}.",
            details={"field": "size_bytes"},
        )
    if kind == "image" and mime_type not in validators.ALLOWED_IMAGE_MIME_TYPES:
        raise ValidationError("Tipo de imagen no permitido.", details={"field": "mime_type"})
    if kind == "model_stl" and mime_type not in validators.ALLOWED_STL_MIME_TYPES:
        raise ValidationError("Tipo de archivo STL no permitido.", details={"field": "mime_type"})

    safe_name = _sanitize_filename(filename)
    storage_key = f"{_kind_prefix(kind)}/{new_ulid()}/{safe_name}"
    expires_in = 600  # 10 minutes
    url = await r2_client.generate_presigned_put_url(
        storage_key=storage_key,
        content_type=mime_type,
        content_length=size_bytes,
        expires_seconds=expires_in,
    )
    return PresignedUpload(
        storage_key=storage_key,
        url=url,
        method="PUT",
        headers={"Content-Type": mime_type},
        expires_at=datetime.now(tz=UTC) + timedelta(seconds=expires_in),
    )


async def commit(
    db: AsyncSession,
    *,
    actor: User,
    storage_key: str,
    kind: str,
    declared_mime_type: str,
    declared_size_bytes: int,
) -> MediaFile:
    if kind not in ADMIN_KINDS:
        raise ValidationError("Tipo de upload no soportado.", details={"field": "kind"})

    head = await r2_client.head_object(storage_key)
    if head is None:
        raise ValidationError(
            "No encontramos el archivo subido. Probá de nuevo.",
            details={"field": "storage_key"},
        )

    actual_size = int(head["content_length"])
    # Grab the first KB to inspect magic bytes / STL header. Cheap regardless
    # of the object's total size.
    read_upto = min(actual_size - 1, 4095)
    head_bytes = await r2_client.get_range(storage_key, start=0, end=read_upto)

    if kind == "image":
        validated = validators.validate_image(
            mime_type=declared_mime_type,
            declared_size=declared_size_bytes,
            actual_size=actual_size,
            head_bytes=head_bytes,
        )
    else:
        validated = validators.validate_stl(
            mime_type=declared_mime_type,
            declared_size=declared_size_bytes,
            actual_size=actual_size,
            head_bytes=head_bytes,
        )

    media = MediaFile(
        owner_user_id=actor.id,
        kind=validated.kind,
        mime_type=validated.mime_type,
        size_bytes=validated.size_bytes,
        storage_key=storage_key,
        public_url=None,
        checksum_sha256=None,
        file_metadata=dict(validated.metadata),
    )
    db.add(media)
    await db.flush()
    await db.refresh(media)
    await audit.log_mutation(
        db,
        actor=actor,
        action=f"media_file.create.{kind}",
        entity_type="media_file",
        entity_id=media.id,
        before=None,
        after=audit.snapshot(media),
    )
    await db.commit()

    # After a successful STL commit, enqueue the conversion job so the
    # frontend eventually has a lightweight GLB to render. Failures are
    # logged inside the helper and do not affect the admin response.
    if validated.kind == "model_stl":
        await media_queue.enqueue_stl_conversion(media.id)

    return media
