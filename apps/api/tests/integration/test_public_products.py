"""Public product endpoints: listing with filters, FTS, pagination, detail."""

from __future__ import annotations

from app.db.session import AsyncSessionLocal
from app.models.automatic_discount import AutomaticDiscount
from app.models.category import Category
from app.models.customization_group import CustomizationGroup
from app.models.customization_option import CustomizationOption
from app.models.product import Product
from app.models.volume_discount import VolumeDiscount
from httpx import AsyncClient


async def _make_category(slug: str = "decoracion", name: str = "Decoración") -> Category:
    async with AsyncSessionLocal() as s:
        c = Category(name=name, slug=slug)
        s.add(c)
        await s.commit()
        await s.refresh(c)
        return c


async def _make_product(
    *,
    category_id: str,
    slug: str,
    name: str,
    price_cents: int = 100000,
    status: str = "active",
    stock_mode: str = "stocked",
    stock_quantity: int | None = 5,
    lead_time_days: int | None = None,
    description: str | None = None,
    tags: list[str] | None = None,
    sku: str | None = None,
) -> Product:
    async with AsyncSessionLocal() as s:
        p = Product(
            category_id=category_id,
            name=name,
            slug=slug,
            description=description,
            base_price_cents=price_cents,
            stock_mode=stock_mode,
            stock_quantity=stock_quantity,
            lead_time_days=lead_time_days,
            sku=sku or f"SKU-{slug.upper()}",
            tags=tags or [],
            status=status,
        )
        s.add(p)
        await s.commit()
        await s.refresh(p)
        return p


# --- Listing ---------------------------------------------------------------


async def test_list_only_active_products(client: AsyncClient) -> None:
    cat = await _make_category()
    await _make_product(category_id=cat.id, slug="visible", name="Visible", status="active")
    await _make_product(category_id=cat.id, slug="draft", name="Draft", status="draft")
    await _make_product(category_id=cat.id, slug="arch", name="Arch", status="archived")

    r = await client.get("/v1/products")
    assert r.status_code == 200
    body = r.json()
    slugs = [p["slug"] for p in body["data"]]
    assert slugs == ["visible"]
    assert body["pagination"]["has_more"] is False
    assert body["data"][0]["category"]["slug"] == "decoracion"
    assert body["data"][0]["availability"] == "in_stock"
    assert body["data"][0]["customizable"] is False


async def test_filter_by_category_slug(client: AsyncClient) -> None:
    c1 = await _make_category(slug="c1", name="C1")
    c2 = await _make_category(slug="c2", name="C2")
    await _make_product(category_id=c1.id, slug="p1", name="P1")
    await _make_product(category_id=c2.id, slug="p2", name="P2")

    r = await client.get("/v1/products?category=c2")
    assert r.status_code == 200
    assert [p["slug"] for p in r.json()["data"]] == ["p2"]


async def test_filter_price_range(client: AsyncClient) -> None:
    cat = await _make_category()
    await _make_product(category_id=cat.id, slug="cheap", name="C", price_cents=5000)
    await _make_product(category_id=cat.id, slug="mid", name="M", price_cents=20000)
    await _make_product(category_id=cat.id, slug="pricey", name="P", price_cents=90000)

    r = await client.get("/v1/products?price_min=10000&price_max=50000")
    assert r.status_code == 200
    assert sorted(p["slug"] for p in r.json()["data"]) == ["mid"]


async def test_filter_availability_on_demand(client: AsyncClient) -> None:
    cat = await _make_category()
    await _make_product(
        category_id=cat.id, slug="stocked", name="S", stock_mode="stocked", stock_quantity=1
    )
    await _make_product(
        category_id=cat.id,
        slug="pod",
        name="POD",
        stock_mode="print_on_demand",
        stock_quantity=None,
        lead_time_days=5,
    )
    r = await client.get("/v1/products?availability=on_demand")
    assert [p["slug"] for p in r.json()["data"]] == ["pod"]


async def test_filter_customizable(client: AsyncClient) -> None:
    cat = await _make_category()
    a = await _make_product(category_id=cat.id, slug="plain", name="Plain")
    b = await _make_product(category_id=cat.id, slug="custom", name="Custom")
    async with AsyncSessionLocal() as s:
        s.add(
            CustomizationGroup(product_id=b.id, name="Color", type="COLOR", selection_mode="single")
        )
        await s.commit()
    _ = a

    r = await client.get("/v1/products?customizable=true")
    assert [p["slug"] for p in r.json()["data"]] == ["custom"]

    r = await client.get("/v1/products?customizable=false")
    assert [p["slug"] for p in r.json()["data"]] == ["plain"]


async def test_search_q_matches_spanish_stem(client: AsyncClient) -> None:
    cat = await _make_category()
    await _make_product(
        category_id=cat.id,
        slug="llavero-perdiz",
        name="Llavero de perdiz",
        description="Pequeño llavero con forma de perdiz.",
    )
    await _make_product(category_id=cat.id, slug="figura", name="Figura decorativa")

    # Spanish stemmer: "llaveros" → "llaver" which matches the stored "llaver"
    # stem from "Llavero". (Note: "perdiz"/"perdices" do NOT collapse via the
    # stemmer, so we don't rely on that pair.)
    r = await client.get("/v1/products?q=llaveros")
    slugs = [p["slug"] for p in r.json()["data"]]
    assert "llavero-perdiz" in slugs
    assert "figura" not in slugs


async def test_search_q_matches_tag(client: AsyncClient) -> None:
    cat = await _make_category()
    await _make_product(
        category_id=cat.id,
        slug="gamer",
        name="Stand para joystick",
        tags=["gaming"],
    )
    await _make_product(category_id=cat.id, slug="nada", name="Otro")

    r = await client.get("/v1/products?q=gaming")
    slugs = [p["slug"] for p in r.json()["data"]]
    assert "gamer" in slugs


async def test_sort_price_asc_and_cursor(client: AsyncClient) -> None:
    cat = await _make_category()
    for i, price in enumerate([100, 200, 300, 400]):
        await _make_product(category_id=cat.id, slug=f"p{i}", name=f"P{i}", price_cents=price)

    r = await client.get("/v1/products?sort=price_asc&limit=2")
    body = r.json()
    assert [p["slug"] for p in body["data"]] == ["p0", "p1"]
    assert body["pagination"]["has_more"] is True
    next_cursor = body["pagination"]["next_cursor"]
    assert next_cursor is not None

    r2 = await client.get(f"/v1/products?sort=price_asc&limit=2&cursor={next_cursor}")
    assert [p["slug"] for p in r2.json()["data"]] == ["p2", "p3"]
    assert r2.json()["pagination"]["has_more"] is False


async def test_discounted_price_reflects_active_automatic_discount(
    client: AsyncClient,
) -> None:
    cat = await _make_category()
    p = await _make_product(category_id=cat.id, slug="discounted", name="D", price_cents=100000)
    async with AsyncSessionLocal() as s:
        s.add(
            AutomaticDiscount(
                name="20% off product",
                type="percentage",
                value=20,
                scope="product",
                target_id=p.id,
            )
        )
        await s.commit()

    r = await client.get("/v1/products")
    row = next(row for row in r.json()["data"] if row["slug"] == "discounted")
    assert row["price_cents"] == 100000
    assert row["discounted_price_cents"] == 80000


# --- Detail ----------------------------------------------------------------


async def test_detail_returns_full_payload(client: AsyncClient) -> None:
    cat = await _make_category()
    p = await _make_product(
        category_id=cat.id,
        slug="detalle",
        name="Detalle",
        price_cents=50000,
        description="<p>descripcion</p>",
        tags=["perdiz", "regalo"],
    )
    async with AsyncSessionLocal() as s:
        group = CustomizationGroup(
            product_id=p.id, name="Color", type="COLOR", selection_mode="single"
        )
        s.add(group)
        await s.flush()
        s.add(CustomizationOption(group_id=group.id, label="Rojo", is_default=True))
        s.add(VolumeDiscount(product_id=p.id, min_quantity=3, type="percentage", value=10))
        s.add(
            AutomaticDiscount(
                name="Cat 10%",
                type="percentage",
                value=10,
                scope="category",
                target_id=cat.id,
            )
        )
        await s.commit()

    r = await client.get("/v1/products/detalle")
    assert r.status_code == 200
    d = r.json()["product"]
    assert d["slug"] == "detalle"
    assert d["base_price_cents"] == 50000
    assert d["discounted_price_cents"] == 45000
    assert d["customizable"] is True
    assert len(d["customization_groups"]) == 1
    assert d["customization_groups"][0]["options"][0]["label"] == "Rojo"
    assert d["volume_discounts"][0]["min_quantity"] == 3
    assert d["tags"] == ["perdiz", "regalo"]


async def test_detail_draft_returns_404(client: AsyncClient) -> None:
    cat = await _make_category()
    await _make_product(category_id=cat.id, slug="borrador", name="Borrador", status="draft")
    r = await client.get("/v1/products/borrador")
    assert r.status_code == 404


async def test_detail_unknown_returns_404(client: AsyncClient) -> None:
    r = await client.get("/v1/products/no-existe")
    assert r.status_code == 404
