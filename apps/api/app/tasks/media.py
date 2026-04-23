"""Background media jobs.

``convert_stl_to_glb`` downloads an STL from R2, converts it to a binary
glTF (GLB) with ``trimesh``, uploads the GLB, and creates a derived
``MediaFile`` row with ``derived_from_id`` pointing at the source STL.

Draco compression is **not** applied at this point. The plain GLB is
already a meaningful improvement over STL for browser rendering (binary
header, indexed geometry). Adding Draco is a follow-up optimisation —
the frontend doesn't need it to work.
"""

from __future__ import annotations

import asyncio
import io
from typing import Any

import structlog
from sqlalchemy import select

from app.db.session import AsyncSessionLocal
from app.models.media_file import MediaFile
from app.services.media import r2_client

log = structlog.get_logger(__name__)


def _stl_to_glb_bytes(stl_bytes: bytes) -> bytes:
    """CPU-bound trimesh conversion. Runs in a thread pool."""
    # Import inside the function so the top-level module stays importable
    # even when trimesh's native deps are not installed in some slim CI
    # images; the job will simply fail at runtime with a clear error.
    import trimesh  # noqa: PLC0415

    mesh = trimesh.load(io.BytesIO(stl_bytes), file_type="stl")
    # trimesh.Geometry.export returns bytes when no file_obj is passed; the
    # signature is loose and mypy can't prove it.
    glb_bytes = mesh.export(file_type="glb")  # type: ignore[no-untyped-call,call-arg]
    assert isinstance(glb_bytes, bytes), "trimesh should return bytes for glb export"
    return glb_bytes


def _derive_glb_storage_key(stl_storage_key: str) -> str:
    """Mirror the STL's storage path under ``models/glb/`` and swap the
    extension to ``.glb``.

    ``models/stl/<ULID>/name.stl`` → ``models/glb/<ULID>/name.glb``.
    """
    # Swap directory prefix.
    glb_key = stl_storage_key.replace("models/stl/", "models/glb/", 1)
    # Swap extension (robust to names without extensions).
    return glb_key[:-4] + ".glb" if glb_key.lower().endswith(".stl") else glb_key + ".glb"


async def convert_stl_to_glb(_ctx: dict[str, Any], stl_media_file_id: str) -> None:
    """Convert the referenced STL into a GLB. Idempotent — if a derived
    GLB already exists for this STL, the job is a no-op.
    """
    async with AsyncSessionLocal() as db:
        stl = await db.get(MediaFile, stl_media_file_id)
        if stl is None or stl.kind != "model_stl" or stl.deleted_at is not None:
            log.warning(
                "stl_convert.skip",
                reason="source_missing",
                media_file_id=stl_media_file_id,
            )
            return

        existing = await db.execute(
            select(MediaFile).where(
                MediaFile.derived_from_id == stl.id,
                MediaFile.kind == "model_glb",
                MediaFile.deleted_at.is_(None),
            )
        )
        if existing.scalar_one_or_none() is not None:
            log.info("stl_convert.skip", reason="already_converted", stl_id=stl.id)
            return

        try:
            stl_bytes = await r2_client.get_object(stl.storage_key)
        except Exception as exc:
            log.error("stl_convert.download_failed", error=str(exc), stl_id=stl.id)
            raise

        try:
            glb_bytes = await asyncio.to_thread(_stl_to_glb_bytes, stl_bytes)
        except Exception as exc:
            log.error("stl_convert.convert_failed", error=str(exc), stl_id=stl.id)
            raise

        glb_key = _derive_glb_storage_key(stl.storage_key)
        await r2_client.put_object(glb_key, glb_bytes, content_type="model/gltf-binary")

        glb = MediaFile(
            owner_user_id=stl.owner_user_id,
            kind="model_glb",
            mime_type="model/gltf-binary",
            size_bytes=len(glb_bytes),
            storage_key=glb_key,
            public_url=None,
            derived_from_id=stl.id,
            file_metadata={
                "converted_from": "model_stl",
                "source_size_bytes": stl.size_bytes,
            },
        )
        db.add(glb)
        await db.commit()
        log.info(
            "stl_convert.done",
            stl_id=stl.id,
            glb_id=glb.id,
            stl_size=stl.size_bytes,
            glb_size=len(glb_bytes),
        )
