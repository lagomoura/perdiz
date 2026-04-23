"""Admin product_images CRUD (metadata; uploads in PR #7)."""

from __future__ import annotations

from app.db.session import AsyncSessionLocal
from app.models.category import Category
from app.models.media_file import MediaFile
from app.models.product import Product
from httpx import AsyncClient

from tests.integration._helpers import auth_header, register_and_promote_admin


async def _setup(
    client: AsyncClient,
) -> tuple[dict[str, str], str, str, str]:
    """Return (headers, product_id, image_media_id, non_image_media_id)."""
    h = auth_header(await register_and_promote_admin(client))
    async with AsyncSessionLocal() as s:
        cat = Category(name="C", slug="c", sort_order=0)
        s.add(cat)
        await s.flush()
        prod = Product(
            category_id=cat.id,
            name="P",
            slug="p",
            base_price_cents=1000,
            stock_mode="stocked",
            stock_quantity=1,
            sku="SKU-P",
            status="active",
        )
        img_media = MediaFile(
            kind="image",
            mime_type="image/webp",
            size_bytes=1024,
            storage_key="img-a.webp",
        )
        stl_media = MediaFile(
            kind="model_stl",
            mime_type="model/stl",
            size_bytes=10000,
            storage_key="model-a.stl",
        )
        s.add(prod)
        s.add(img_media)
        s.add(stl_media)
        await s.commit()
        await s.refresh(prod)
        await s.refresh(img_media)
        await s.refresh(stl_media)
        return h, prod.id, img_media.id, stl_media.id


async def test_add_image_ok(client: AsyncClient) -> None:
    h, pid, img_id, _ = await _setup(client)
    r = await client.post(
        f"/v1/admin/products/{pid}/images",
        json={"media_file_id": img_id, "alt_text": "Foto principal", "sort_order": 0},
        headers=h,
    )
    assert r.status_code == 201, r.text
    assert r.json()["image"]["media_file_id"] == img_id
    assert r.json()["image"]["alt_text"] == "Foto principal"


async def test_reject_non_image_media(client: AsyncClient) -> None:
    h, pid, _, stl_id = await _setup(client)
    r = await client.post(
        f"/v1/admin/products/{pid}/images",
        json={"media_file_id": stl_id, "alt_text": None, "sort_order": 0},
        headers=h,
    )
    assert r.status_code == 422
    assert r.json()["error"]["code"] == "VALIDATION_ERROR"


async def test_reject_unknown_media(client: AsyncClient) -> None:
    h, pid, _, _ = await _setup(client)
    r = await client.post(
        f"/v1/admin/products/{pid}/images",
        json={
            "media_file_id": "01HWFAKEFAKEFAKEFAKEFAKEFA",
            "alt_text": None,
            "sort_order": 0,
        },
        headers=h,
    )
    assert r.status_code == 422


async def test_update_alt_and_sort_order(client: AsyncClient) -> None:
    h, pid, img_id, _ = await _setup(client)
    created = (
        await client.post(
            f"/v1/admin/products/{pid}/images",
            json={"media_file_id": img_id, "alt_text": "vieja", "sort_order": 0},
            headers=h,
        )
    ).json()["image"]

    r = await client.patch(
        f"/v1/admin/products/{pid}/images/{created['id']}",
        json={"alt_text": "nueva", "sort_order": 3},
        headers=h,
    )
    assert r.status_code == 200
    body = r.json()["image"]
    assert body["alt_text"] == "nueva"
    assert body["sort_order"] == 3


async def test_list_and_delete(client: AsyncClient) -> None:
    h, pid, img_id, _ = await _setup(client)
    created = (
        await client.post(
            f"/v1/admin/products/{pid}/images",
            json={"media_file_id": img_id, "alt_text": None, "sort_order": 0},
            headers=h,
        )
    ).json()["image"]

    listing = await client.get(f"/v1/admin/products/{pid}/images", headers=h)
    assert len(listing.json()["data"]) == 1

    r = await client.delete(f"/v1/admin/products/{pid}/images/{created['id']}", headers=h)
    assert r.status_code == 204

    listing2 = await client.get(f"/v1/admin/products/{pid}/images", headers=h)
    assert listing2.json()["data"] == []
