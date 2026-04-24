import type { ProductImage } from '@/types/catalog';

import { apiFetch } from './api/client';

interface ProductImageApi {
  id: string;
  product_id: string;
  media_file_id: string;
  alt_text: string | null;
  sort_order: number;
  url: string | null;
}

function fromApi(i: ProductImageApi): ProductImage {
  return {
    id: i.id,
    productId: i.product_id,
    mediaFileId: i.media_file_id,
    altText: i.alt_text,
    sortOrder: i.sort_order,
    url: i.url,
  };
}

export async function listProductImages(
  productId: string,
): Promise<ProductImage[]> {
  const res = await apiFetch<{ data: ProductImageApi[] }>(
    `/admin/products/${productId}/images`,
  );
  return res.data.map(fromApi);
}

export async function createProductImage(
  productId: string,
  payload: { mediaFileId: string; altText?: string | null; sortOrder?: number },
): Promise<ProductImage> {
  const res = await apiFetch<{ image: ProductImageApi }>(
    `/admin/products/${productId}/images`,
    {
      method: 'POST',
      body: JSON.stringify({
        media_file_id: payload.mediaFileId,
        alt_text: payload.altText ?? null,
        sort_order: payload.sortOrder ?? 0,
      }),
    },
  );
  return fromApi(res.image);
}

export async function updateProductImage(
  productId: string,
  imageId: string,
  payload: { altText?: string | null; sortOrder?: number },
): Promise<ProductImage> {
  const body: Record<string, unknown> = {};
  if (payload.altText !== undefined) body.alt_text = payload.altText;
  if (payload.sortOrder !== undefined) body.sort_order = payload.sortOrder;
  const res = await apiFetch<{ image: ProductImageApi }>(
    `/admin/products/${productId}/images/${imageId}`,
    {
      method: 'PATCH',
      body: JSON.stringify(body),
    },
  );
  return fromApi(res.image);
}

export async function deleteProductImage(
  productId: string,
  imageId: string,
): Promise<void> {
  await apiFetch<void>(`/admin/products/${productId}/images/${imageId}`, {
    method: 'DELETE',
  });
}
