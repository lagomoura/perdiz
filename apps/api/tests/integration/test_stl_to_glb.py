"""STL → GLB conversion job.

Exercises the pure conversion function against real MinIO storage without
spinning up an arq worker. The enqueue side of the flow is covered in
``test_admin_uploads`` by monkey-patching the queue helper.
"""

from __future__ import annotations

import struct
from typing import Any

from app.db.session import AsyncSessionLocal
from app.models.media_file import MediaFile
from app.services.media import r2_client
from app.tasks.media import _derive_glb_storage_key, convert_stl_to_glb
from sqlalchemy import select


# A minimal but valid binary STL with 2 triangles. trimesh accepts this.
def _valid_stl(triangles: int = 2) -> bytes:
    header = b"p3rdiz test stl".ljust(80, b"\x00")
    parts = [header, struct.pack("<I", triangles)]
    # Each triangle: 3 normal floats, 3 vertex floats x 3, uint16 attr.
    # Produce a degenerate but parseable triangle (all zeros).
    for _ in range(triangles):
        parts.append(b"\x00" * 50)
    return b"".join(parts)


async def _insert_stl_media(storage_key: str, size: int) -> MediaFile:
    async with AsyncSessionLocal() as s:
        media = MediaFile(
            owner_user_id=None,
            kind="model_stl",
            mime_type="model/stl",
            size_bytes=size,
            storage_key=storage_key,
            file_metadata={"format": "binary", "triangles": 2},
        )
        s.add(media)
        await s.commit()
        await s.refresh(media)
        return media


def test_derive_glb_key() -> None:
    assert (
        _derive_glb_storage_key("models/stl/01HWXYZ/perdiz.stl") == "models/glb/01HWXYZ/perdiz.glb"
    )
    # Fallback for missing extension.
    assert _derive_glb_storage_key("models/stl/01HWXYZ/perdiz") == "models/glb/01HWXYZ/perdiz.glb"


async def test_convert_creates_derived_glb() -> None:
    stl_bytes = _valid_stl(triangles=3)
    stl_key = "models/stl/01HWTESTSTL/sample.stl"
    await r2_client.put_object(stl_key, stl_bytes, content_type="model/stl")
    stl_media = await _insert_stl_media(stl_key, len(stl_bytes))

    ctx: dict[str, Any] = {}
    await convert_stl_to_glb(ctx, stl_media.id)

    async with AsyncSessionLocal() as s:
        rows = (
            (await s.execute(select(MediaFile).where(MediaFile.derived_from_id == stl_media.id)))
            .scalars()
            .all()
        )
        assert len(rows) == 1
        glb = rows[0]
        assert glb.kind == "model_glb"
        assert glb.mime_type == "model/gltf-binary"
        assert glb.storage_key == "models/glb/01HWTESTSTL/sample.glb"
        assert glb.size_bytes > 0
        assert glb.file_metadata["converted_from"] == "model_stl"

    # The GLB object actually made it to R2.
    head = await r2_client.head_object(glb.storage_key)
    assert head is not None
    assert head["content_length"] == glb.size_bytes


async def test_convert_is_idempotent() -> None:
    stl_bytes = _valid_stl(triangles=2)
    stl_key = "models/stl/01HWTESTIDEMP/sample.stl"
    await r2_client.put_object(stl_key, stl_bytes, content_type="model/stl")
    stl_media = await _insert_stl_media(stl_key, len(stl_bytes))

    ctx: dict[str, Any] = {}
    await convert_stl_to_glb(ctx, stl_media.id)
    await convert_stl_to_glb(ctx, stl_media.id)  # second call

    async with AsyncSessionLocal() as s:
        rows = (
            (await s.execute(select(MediaFile).where(MediaFile.derived_from_id == stl_media.id)))
            .scalars()
            .all()
        )
        assert len(rows) == 1, "second run must not create a duplicate GLB"


async def test_convert_skips_when_source_missing() -> None:
    # Should not raise. Just logs and returns.
    await convert_stl_to_glb({}, "01HWDOESNOTEXISTDOESNOTEXIST")


async def test_convert_skips_when_source_is_not_stl() -> None:
    async with AsyncSessionLocal() as s:
        media = MediaFile(
            kind="image",
            mime_type="image/png",
            size_bytes=10,
            storage_key="images/nope/not-stl.png",
        )
        s.add(media)
        await s.commit()
        await s.refresh(media)
        mid = media.id

    # Should short-circuit without hitting R2 or trimesh.
    await convert_stl_to_glb({}, mid)
    async with AsyncSessionLocal() as s:
        rows = (
            (await s.execute(select(MediaFile).where(MediaFile.derived_from_id == mid)))
            .scalars()
            .all()
        )
        assert rows == []
