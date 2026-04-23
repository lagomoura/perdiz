"""``cleanup_abandoned_uploads`` job."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from app.db.session import AsyncSessionLocal
from app.models.category import Category
from app.models.media_file import MediaFile
from app.models.product import Product
from app.models.product_image import ProductImage
from app.services.media import r2_client
from app.tasks.media import CLEANUP_AGE_HOURS, cleanup_abandoned_uploads
from sqlalchemy import select, update


async def _make_media(
    *,
    storage_key: str,
    kind: str = "user_upload_image",
    age_hours: float,
) -> MediaFile:
    """Create a MediaFile with a backdated ``created_at``."""
    async with AsyncSessionLocal() as s:
        media = MediaFile(
            kind=kind,
            mime_type="image/png" if kind.endswith("image") else "model/stl",
            size_bytes=100,
            storage_key=storage_key,
        )
        s.add(media)
        await s.commit()
        await s.refresh(media)
        mid = media.id

    # Backdate separately because server_default=now() is set at insert.
    async with AsyncSessionLocal() as s:
        await s.execute(
            update(MediaFile)
            .where(MediaFile.id == mid)
            .values(created_at=datetime.now(tz=UTC) - timedelta(hours=age_hours))
        )
        await s.commit()

    async with AsyncSessionLocal() as s:
        return (await s.execute(select(MediaFile).where(MediaFile.id == mid))).scalar_one()


async def _put_dummy(storage_key: str) -> None:
    await r2_client.put_object(storage_key, b"x", content_type="application/octet-stream")


async def test_cleanup_deletes_old_orphan() -> None:
    key = "uploads/images/01HWCLEANUP_OLD/orphan.png"
    await _put_dummy(key)
    await _make_media(storage_key=key, age_hours=CLEANUP_AGE_HOURS + 1)

    deleted = await cleanup_abandoned_uploads({})
    assert deleted >= 1

    async with AsyncSessionLocal() as s:
        rows = (
            (await s.execute(select(MediaFile).where(MediaFile.storage_key == key))).scalars().all()
        )
        assert rows == []

    assert await r2_client.head_object(key) is None


async def test_cleanup_keeps_recent_orphan() -> None:
    key = "uploads/images/01HWCLEANUP_NEW/orphan.png"
    await _put_dummy(key)
    await _make_media(storage_key=key, age_hours=1)

    await cleanup_abandoned_uploads({})

    async with AsyncSessionLocal() as s:
        row = (
            await s.execute(select(MediaFile).where(MediaFile.storage_key == key))
        ).scalar_one_or_none()
        assert row is not None  # still here


async def test_cleanup_keeps_referenced_by_product_image() -> None:
    key = "images/01HWCLEANUP_REFPROD/foto.png"
    await _put_dummy(key)
    media = await _make_media(storage_key=key, kind="image", age_hours=CLEANUP_AGE_HOURS + 2)

    async with AsyncSessionLocal() as s:
        cat = Category(name="C", slug="c-cleanup", sort_order=0)
        s.add(cat)
        await s.flush()
        p = Product(
            category_id=cat.id,
            name="P",
            slug="p-cleanup",
            base_price_cents=1000,
            stock_mode="stocked",
            stock_quantity=1,
            sku="SKU-PCL",
            status="active",
        )
        s.add(p)
        await s.flush()
        s.add(ProductImage(product_id=p.id, media_file_id=media.id, sort_order=0))
        await s.commit()

    await cleanup_abandoned_uploads({})

    async with AsyncSessionLocal() as s:
        row = (
            await s.execute(select(MediaFile).where(MediaFile.id == media.id))
        ).scalar_one_or_none()
        assert row is not None, "media referenced by product_image must survive"


async def test_cleanup_keeps_stl_when_glb_derived_exists() -> None:
    stl_key = "models/stl/01HWCLEANUP_STL/a.stl"
    await _put_dummy(stl_key)
    stl = await _make_media(storage_key=stl_key, kind="model_stl", age_hours=CLEANUP_AGE_HOURS + 5)

    glb_key = "models/glb/01HWCLEANUP_STL/a.glb"
    await _put_dummy(glb_key)
    async with AsyncSessionLocal() as s:
        glb = MediaFile(
            kind="model_glb",
            mime_type="model/gltf-binary",
            size_bytes=50,
            storage_key=glb_key,
            derived_from_id=stl.id,
        )
        s.add(glb)
        await s.commit()

    await cleanup_abandoned_uploads({})

    async with AsyncSessionLocal() as s:
        survived = (
            await s.execute(select(MediaFile).where(MediaFile.id == stl.id))
        ).scalar_one_or_none()
        assert survived is not None, "STL referenced by derived GLB must survive"
