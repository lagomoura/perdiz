"""Public category endpoints."""

from __future__ import annotations

from app.db.session import AsyncSessionLocal
from app.models.category import Category
from httpx import AsyncClient


async def _seed_categories() -> None:
    async with AsyncSessionLocal() as s:
        s.add(Category(name="Decoración", slug="decoracion", sort_order=1))
        s.add(Category(name="Llaveros", slug="llaveros", sort_order=2))
        s.add(Category(name="Archivada", slug="archivada", sort_order=3, status="archived"))
        await s.commit()


async def test_list_returns_only_active_sorted(client: AsyncClient) -> None:
    await _seed_categories()
    r = await client.get("/v1/categories")
    assert r.status_code == 200
    body = r.json()
    slugs = [c["slug"] for c in body["data"]]
    assert slugs == ["decoracion", "llaveros"]
    assert all("sort_order" in c for c in body["data"])


async def test_detail_by_slug(client: AsyncClient) -> None:
    await _seed_categories()
    r = await client.get("/v1/categories/llaveros")
    assert r.status_code == 200
    assert r.json()["category"]["slug"] == "llaveros"


async def test_detail_archived_returns_404(client: AsyncClient) -> None:
    await _seed_categories()
    r = await client.get("/v1/categories/archivada")
    assert r.status_code == 404
    assert r.json()["error"]["code"] == "NOT_FOUND"


async def test_detail_unknown_returns_404(client: AsyncClient) -> None:
    r = await client.get("/v1/categories/no-existe")
    assert r.status_code == 404
