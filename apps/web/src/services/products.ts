import type {
  Product,
  ProductCreatePayload,
  ProductStatus,
  ProductUpdatePayload,
} from '@/types/catalog';

import { apiFetch } from './api/client';

interface ProductApi {
  id: string;
  category_id: string;
  name: string;
  slug: string;
  description: string | null;
  base_price_cents: number;
  stock_mode: 'stocked' | 'print_on_demand';
  stock_quantity: number | null;
  lead_time_days: number | null;
  weight_grams: number | null;
  dimensions_mm: number[] | null;
  sku: string;
  tags: string[];
  status: ProductStatus;
  model_file_id: string | null;
  created_at: string;
  updated_at: string;
  deleted_at: string | null;
}

function fromApi(p: ProductApi): Product {
  return {
    id: p.id,
    categoryId: p.category_id,
    name: p.name,
    slug: p.slug,
    description: p.description,
    basePriceCents: p.base_price_cents,
    stockMode: p.stock_mode,
    stockQuantity: p.stock_quantity,
    leadTimeDays: p.lead_time_days,
    weightGrams: p.weight_grams,
    dimensionsMm: p.dimensions_mm,
    sku: p.sku,
    tags: p.tags,
    status: p.status,
    modelFileId: p.model_file_id,
    createdAt: p.created_at,
    updatedAt: p.updated_at,
    deletedAt: p.deleted_at,
  };
}

function toCreateBody(p: ProductCreatePayload): Record<string, unknown> {
  return {
    category_id: p.categoryId,
    name: p.name,
    slug: p.slug,
    description: p.description ?? null,
    base_price_cents: p.basePriceCents,
    stock_mode: p.stockMode,
    stock_quantity: p.stockQuantity ?? null,
    lead_time_days: p.leadTimeDays ?? null,
    weight_grams: p.weightGrams ?? null,
    dimensions_mm: p.dimensionsMm ?? null,
    sku: p.sku,
    tags: p.tags ?? [],
    status: p.status ?? 'draft',
    model_file_id: p.modelFileId ?? null,
  };
}

function toUpdateBody(p: ProductUpdatePayload): Record<string, unknown> {
  const b: Record<string, unknown> = {};
  if (p.categoryId !== undefined) b.category_id = p.categoryId;
  if (p.name !== undefined) b.name = p.name;
  if (p.slug !== undefined) b.slug = p.slug;
  if (p.description !== undefined) b.description = p.description;
  if (p.basePriceCents !== undefined) b.base_price_cents = p.basePriceCents;
  if (p.stockMode !== undefined) b.stock_mode = p.stockMode;
  if (p.stockQuantity !== undefined) b.stock_quantity = p.stockQuantity;
  if (p.leadTimeDays !== undefined) b.lead_time_days = p.leadTimeDays;
  if (p.weightGrams !== undefined) b.weight_grams = p.weightGrams;
  if (p.dimensionsMm !== undefined) b.dimensions_mm = p.dimensionsMm;
  if (p.sku !== undefined) b.sku = p.sku;
  if (p.tags !== undefined) b.tags = p.tags;
  if (p.status !== undefined) b.status = p.status;
  if (p.modelFileId !== undefined) b.model_file_id = p.modelFileId;
  return b;
}

export interface ListProductsOpts {
  status?: ProductStatus;
  categoryId?: string;
  limit?: number;
  offset?: number;
}

export interface ProductsListResult {
  data: Product[];
  count: number;
}

export async function listProducts(
  opts: ListProductsOpts = {},
): Promise<ProductsListResult> {
  const qs = new URLSearchParams();
  if (opts.status) qs.set('status', opts.status);
  if (opts.categoryId) qs.set('category_id', opts.categoryId);
  qs.set('limit', String(opts.limit ?? 50));
  qs.set('offset', String(opts.offset ?? 0));
  const res = await apiFetch<{ data: ProductApi[]; count: number }>(
    `/admin/products?${qs.toString()}`,
  );
  return { data: res.data.map(fromApi), count: res.count };
}

export async function getProduct(id: string): Promise<Product> {
  const res = await apiFetch<{ product: ProductApi }>(`/admin/products/${id}`);
  return fromApi(res.product);
}

export async function createProduct(
  payload: ProductCreatePayload,
): Promise<Product> {
  const res = await apiFetch<{ product: ProductApi }>('/admin/products', {
    method: 'POST',
    body: JSON.stringify(toCreateBody(payload)),
  });
  return fromApi(res.product);
}

export async function updateProduct(
  id: string,
  payload: ProductUpdatePayload,
): Promise<Product> {
  const res = await apiFetch<{ product: ProductApi }>(`/admin/products/${id}`, {
    method: 'PATCH',
    body: JSON.stringify(toUpdateBody(payload)),
  });
  return fromApi(res.product);
}

export async function transitionProductStatus(
  id: string,
  status: ProductStatus,
): Promise<Product> {
  const res = await apiFetch<{ product: ProductApi }>(
    `/admin/products/${id}/transition-status`,
    {
      method: 'POST',
      body: JSON.stringify({ status }),
    },
  );
  return fromApi(res.product);
}

export async function deleteProduct(id: string): Promise<void> {
  await apiFetch<void>(`/admin/products/${id}`, { method: 'DELETE' });
}
