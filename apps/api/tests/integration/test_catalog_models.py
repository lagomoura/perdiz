"""Integration tests for catalog model constraints and generated columns."""

from __future__ import annotations

import pytest
from app.db.session import AsyncSessionLocal
from app.models.automatic_discount import AutomaticDiscount
from app.models.category import Category
from app.models.customization_group import CustomizationGroup
from app.models.customization_option import CustomizationOption
from app.models.media_file import MediaFile
from app.models.product import Product
from app.models.product_image import ProductImage
from app.models.volume_discount import VolumeDiscount
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError


async def _make_category(name: str = "Decoración", slug: str = "decoracion") -> Category:
    async with AsyncSessionLocal() as s:
        c = Category(name=name, slug=slug)
        s.add(c)
        await s.commit()
        await s.refresh(c)
        return c


async def test_category_slug_is_unique() -> None:
    await _make_category(slug="duplicado")
    with pytest.raises(IntegrityError):
        async with AsyncSessionLocal() as s:
            s.add(Category(name="Otro", slug="duplicado"))
            await s.commit()


async def test_product_base_price_must_be_non_negative() -> None:
    cat = await _make_category(slug="p-price")
    with pytest.raises(IntegrityError):
        async with AsyncSessionLocal() as s:
            s.add(
                Product(
                    category_id=cat.id,
                    name="Negativo",
                    slug="negativo",
                    base_price_cents=-1,
                    stock_mode="stocked",
                    stock_quantity=1,
                    sku="SKU-NEG",
                )
            )
            await s.commit()


async def test_product_stock_mode_stocked_requires_stock_quantity() -> None:
    cat = await _make_category(slug="p-stocked-bad")
    with pytest.raises(IntegrityError):
        async with AsyncSessionLocal() as s:
            s.add(
                Product(
                    category_id=cat.id,
                    name="Stocked sin cantidad",
                    slug="stocked-sin-cantidad",
                    base_price_cents=100,
                    stock_mode="stocked",
                    stock_quantity=None,
                    sku="SKU-SSQ",
                )
            )
            await s.commit()


async def test_product_print_on_demand_requires_lead_time() -> None:
    cat = await _make_category(slug="p-pod-bad")
    with pytest.raises(IntegrityError):
        async with AsyncSessionLocal() as s:
            s.add(
                Product(
                    category_id=cat.id,
                    name="POD sin lead time",
                    slug="pod-sin-lead",
                    base_price_cents=100,
                    stock_mode="print_on_demand",
                    lead_time_days=None,
                    sku="SKU-POD",
                )
            )
            await s.commit()


async def test_product_search_tsv_is_populated() -> None:
    cat = await _make_category(slug="p-tsv")
    async with AsyncSessionLocal() as s:
        p = Product(
            category_id=cat.id,
            name="Llavero de perdiz",
            slug="llavero-perdiz",
            description="Un llavero con forma de perdiz low-poly.",
            base_price_cents=150000,
            stock_mode="stocked",
            stock_quantity=10,
            sku="SKU-TSV-001",
        )
        s.add(p)
        await s.commit()

    async with AsyncSessionLocal() as s:
        result = await s.execute(
            text(
                "SELECT search_tsv @@ to_tsquery('spanish'::regconfig, 'perdiz') "
                "FROM products WHERE sku = 'SKU-TSV-001'"
            )
        )
        (matched,) = result.one()
        assert matched is True


async def test_product_deletes_cascade_to_images_groups_and_volume_discounts() -> None:
    cat = await _make_category(slug="p-cascade")
    async with AsyncSessionLocal() as s:
        media = MediaFile(
            kind="image",
            mime_type="image/webp",
            size_bytes=1024,
            storage_key="cascade-img.webp",
        )
        s.add(media)
        await s.flush()

        product = Product(
            category_id=cat.id,
            name="Prueba cascada",
            slug="prueba-cascada",
            base_price_cents=5000,
            stock_mode="print_on_demand",
            lead_time_days=3,
            sku="SKU-CASC",
        )
        s.add(product)
        await s.flush()

        s.add(ProductImage(product_id=product.id, media_file_id=media.id, sort_order=0))
        group = CustomizationGroup(
            product_id=product.id, name="Color", type="COLOR", selection_mode="single"
        )
        s.add(group)
        await s.flush()
        s.add(CustomizationOption(group_id=group.id, label="Rojo"))
        s.add(VolumeDiscount(product_id=product.id, min_quantity=3, type="percentage", value=10))
        await s.commit()

        await s.delete(product)
        await s.commit()

    async with AsyncSessionLocal() as s:
        assert (await s.execute(select(ProductImage))).scalars().first() is None
        assert (await s.execute(select(CustomizationGroup))).scalars().first() is None
        assert (await s.execute(select(CustomizationOption))).scalars().first() is None
        assert (await s.execute(select(VolumeDiscount))).scalars().first() is None
        # MediaFile has ON DELETE RESTRICT from product_images → removing product_image first,
        # so MediaFile survives.
        assert (await s.execute(select(MediaFile))).scalars().first() is not None


async def test_volume_discount_min_quantity_constraint() -> None:
    cat = await _make_category(slug="p-vd")
    async with AsyncSessionLocal() as s:
        product = Product(
            category_id=cat.id,
            name="VD test",
            slug="vd-test",
            base_price_cents=1000,
            stock_mode="stocked",
            stock_quantity=10,
            sku="SKU-VD",
        )
        s.add(product)
        await s.commit()
        product_id = product.id

    with pytest.raises(IntegrityError):
        async with AsyncSessionLocal() as s:
            s.add(VolumeDiscount(product_id=product_id, min_quantity=1, type="fixed", value=100))
            await s.commit()


async def test_automatic_discount_value_must_be_positive() -> None:
    with pytest.raises(IntegrityError):
        async with AsyncSessionLocal() as s:
            s.add(
                AutomaticDiscount(
                    name="Inválido",
                    type="percentage",
                    value=0,
                    scope="category",
                    target_id="01HWFAKEHWFAKEHWFAKEHWFAK",
                )
            )
            await s.commit()
