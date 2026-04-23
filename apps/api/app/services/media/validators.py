"""Post-upload validation helpers.

These run after the object landed in R2 (via the client's PUT with the
presigned URL). The server does a short Range GET to read the file's header
and verify:

- Image files: magic bytes match the declared ``content_type``.
- Binary STL files: header is 80 bytes + 4-byte little-endian triangle count
  and ``header_size + triangle_count * 50`` equals the object's size.

Keeping validation header-only (≤ 4KB) so it's cheap even for a 100MB STL.
"""

from __future__ import annotations

import struct
from dataclasses import dataclass

from app.exceptions import ValidationError

ALLOWED_IMAGE_MIME_TYPES: frozenset[str] = frozenset({"image/jpeg", "image/png", "image/webp"})
ALLOWED_STL_MIME_TYPES: frozenset[str] = frozenset(
    # Browsers vary — allow the common ones + the fallback octet-stream.
    {
        "model/stl",
        "application/sla",
        "application/vnd.ms-pki.stl",
        "application/octet-stream",
    }
)

MAX_IMAGE_BYTES: int = 5 * 1024 * 1024  # 5 MB
MAX_STL_BYTES: int = 100 * 1024 * 1024  # 100 MB


@dataclass(frozen=True)
class ValidatedUpload:
    kind: str
    mime_type: str
    size_bytes: int
    metadata: dict[str, object]


def _mime_matches_magic(content_type: str, head: bytes) -> bool:
    if content_type == "image/jpeg":
        return head.startswith(b"\xff\xd8\xff")
    if content_type == "image/png":
        return head.startswith(b"\x89PNG\r\n\x1a\n")
    if content_type == "image/webp":
        return head.startswith(b"RIFF") and len(head) >= 12 and head[8:12] == b"WEBP"
    return False


def validate_image(
    *, mime_type: str, declared_size: int, actual_size: int, head_bytes: bytes
) -> ValidatedUpload:
    if mime_type not in ALLOWED_IMAGE_MIME_TYPES:
        raise ValidationError("Tipo de imagen no permitido.", details={"field": "mime_type"})
    if actual_size != declared_size:
        raise ValidationError(
            "El tamaño del archivo no coincide con el declarado.",
            details={"field": "size_bytes"},
        )
    if actual_size > MAX_IMAGE_BYTES:
        raise ValidationError(
            "La imagen supera el tamaño máximo (5 MB).",
            details={"field": "size_bytes"},
        )
    if not _mime_matches_magic(mime_type, head_bytes):
        raise ValidationError(
            "El contenido del archivo no coincide con el mime_type.",
            details={"field": "content"},
        )
    return ValidatedUpload(kind="image", mime_type=mime_type, size_bytes=actual_size, metadata={})


def validate_stl(
    *, mime_type: str, declared_size: int, actual_size: int, head_bytes: bytes
) -> ValidatedUpload:
    if mime_type not in ALLOWED_STL_MIME_TYPES:
        raise ValidationError("Tipo de archivo STL no permitido.", details={"field": "mime_type"})
    if actual_size != declared_size:
        raise ValidationError(
            "El tamaño del archivo no coincide con el declarado.",
            details={"field": "size_bytes"},
        )
    if actual_size > MAX_STL_BYTES:
        raise ValidationError(
            "El STL supera el tamaño máximo (100 MB).",
            details={"field": "size_bytes"},
        )
    if actual_size < 84:
        # Binary STL header is 80 bytes + uint32 triangle count.
        raise ValidationError(
            "El archivo STL es demasiado chico para ser válido.",
            details={"field": "content"},
        )

    # Plausibility check on binary STL only (ASCII STL starts with "solid ").
    is_ascii = head_bytes[:6].lower() == b"solid "
    triangles: int | None = None
    if not is_ascii and len(head_bytes) >= 84:
        (triangles,) = struct.unpack("<I", head_bytes[80:84])
        expected_size = 84 + triangles * 50
        # Tolerate small off-by-header variations from some exporters, but
        # reject values wildly inconsistent with the actual size.
        if abs(expected_size - actual_size) > 100 or triangles > 50_000_000:
            raise ValidationError(
                "El archivo STL parece estar corrupto o no ser binario.",
                details={"field": "content"},
            )

    metadata: dict[str, object] = {"format": "ascii" if is_ascii else "binary"}
    if triangles is not None:
        metadata["triangles"] = triangles
    return ValidatedUpload(
        kind="model_stl", mime_type=mime_type, size_bytes=actual_size, metadata=metadata
    )
