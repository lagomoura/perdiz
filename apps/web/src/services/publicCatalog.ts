import type {
  Availability,
  CatalogSort,
  PublicCategory,
  PublicProduct,
  PublicProductDetail,
  PublicProductsPage,
} from '@/types/catalog';

import { apiFetch } from './api/client';

interface CategoryApi {
  id: string;
  name: string;
  slug: string;
  description: string | null;
  image_url: string | null;
  sort_order: number;
}

function categoryFromApi(c: CategoryApi): PublicCategory {
  return {
    id: c.id,
    name: c.name,
    slug: c.slug,
    description: c.description,
    imageUrl: c.image_url,
    sortOrder: c.sort_order,
  };
}

export async function listPublicCategories(): Promise<PublicCategory[]> {
  const res = await apiFetch<{ data: CategoryApi[] }>('/categories');
  return res.data.map(categoryFromApi);
}

interface ProductListItemApi {
  id: string;
  name: string;
  slug: string;
  price_cents: number;
  discounted_price_cents: number | null;
  currency: 'ARS';
  images: { url: string; alt: string | null }[];
  category: { id: string; name: string; slug: string };
  availability: Availability;
  customizable: boolean;
  tags: string[];
}

interface ProductListApi {
  data: ProductListItemApi[];
  pagination: {
    next_cursor: string | null;
    has_more: boolean;
    count: number;
  };
}

function productFromApi(p: ProductListItemApi): PublicProduct {
  return {
    id: p.id,
    name: p.name,
    slug: p.slug,
    priceCents: p.price_cents,
    discountedPriceCents: p.discounted_price_cents,
    currency: p.currency,
    images: p.images.map((i) => ({ url: i.url, alt: i.alt })),
    category: { id: p.category.id, name: p.category.name, slug: p.category.slug },
    availability: p.availability,
    customizable: p.customizable,
    tags: p.tags,
  };
}

export interface ListPublicProductsOpts {
  q?: string;
  category?: string;
  priceMin?: number;
  priceMax?: number;
  availability?: Availability;
  customizable?: boolean;
  sort?: CatalogSort;
  cursor?: string;
  limit?: number;
}

export async function listPublicProducts(
  opts: ListPublicProductsOpts = {},
): Promise<PublicProductsPage> {
  const qs = new URLSearchParams();
  if (opts.q) qs.set('q', opts.q);
  if (opts.category) qs.set('category', opts.category);
  if (opts.priceMin !== undefined) qs.set('price_min', String(opts.priceMin));
  if (opts.priceMax !== undefined) qs.set('price_max', String(opts.priceMax));
  if (opts.availability) qs.set('availability', opts.availability);
  if (opts.customizable !== undefined)
    qs.set('customizable', String(opts.customizable));
  if (opts.sort) qs.set('sort', opts.sort);
  if (opts.cursor) qs.set('cursor', opts.cursor);
  qs.set('limit', String(opts.limit ?? 24));

  const res = await apiFetch<ProductListApi>(`/products?${qs.toString()}`);
  return {
    data: res.data.map(productFromApi),
    pagination: {
      nextCursor: res.pagination.next_cursor,
      hasMore: res.pagination.has_more,
      count: res.pagination.count,
    },
  };
}

interface ProductDetailApi {
  id: string;
  name: string;
  slug: string;
  description_html: string | null;
  base_price_cents: number;
  discounted_price_cents: number | null;
  currency: 'ARS';
  category: { id: string; name: string; slug: string };
  images: { url: string; alt: string | null }[];
  model_glb_url: string | null;
  stock_mode: 'stocked' | 'print_on_demand';
  stock_quantity: number | null;
  lead_time_days: number | null;
  availability: Availability;
  customizable: boolean;
}

function detailFromApi(p: ProductDetailApi): PublicProductDetail {
  return {
    id: p.id,
    name: p.name,
    slug: p.slug,
    descriptionHtml: p.description_html,
    basePriceCents: p.base_price_cents,
    discountedPriceCents: p.discounted_price_cents,
    currency: p.currency,
    category: p.category,
    images: p.images.map((i) => ({ url: i.url, alt: i.alt })),
    modelGlbUrl: p.model_glb_url,
    stockMode: p.stock_mode,
    stockQuantity: p.stock_quantity,
    leadTimeDays: p.lead_time_days,
    availability: p.availability,
    customizable: p.customizable,
  };
}

export async function getPublicProduct(
  slug: string,
): Promise<PublicProductDetail> {
  const res = await apiFetch<{ product: ProductDetailApi }>(`/products/${slug}`);
  return detailFromApi(res.product);
}
