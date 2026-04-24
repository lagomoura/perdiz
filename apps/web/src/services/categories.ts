import type {
  Category,
  CategoryCreatePayload,
  CategoryStatus,
  CategoryUpdatePayload,
} from '@/types/catalog';

import { apiFetch } from './api/client';

interface CategoryApi {
  id: string;
  name: string;
  slug: string;
  parent_id: string | null;
  description: string | null;
  image_url: string | null;
  sort_order: number;
  status: CategoryStatus;
  created_at: string;
  updated_at: string;
  deleted_at: string | null;
}

function fromApi(c: CategoryApi): Category {
  return {
    id: c.id,
    name: c.name,
    slug: c.slug,
    parentId: c.parent_id,
    description: c.description,
    imageUrl: c.image_url,
    sortOrder: c.sort_order,
    status: c.status,
    createdAt: c.created_at,
    updatedAt: c.updated_at,
    deletedAt: c.deleted_at,
  };
}

export async function listCategories(opts?: {
  status?: CategoryStatus;
}): Promise<Category[]> {
  const qs = opts?.status ? `?status=${opts.status}` : '';
  const data = await apiFetch<{ data: CategoryApi[] }>(`/admin/categories${qs}`);
  return data.data.map(fromApi);
}

export async function getCategory(id: string): Promise<Category> {
  const data = await apiFetch<{ category: CategoryApi }>(`/admin/categories/${id}`);
  return fromApi(data.category);
}

export async function createCategory(
  payload: CategoryCreatePayload,
): Promise<Category> {
  const data = await apiFetch<{ category: CategoryApi }>('/admin/categories', {
    method: 'POST',
    body: JSON.stringify({
      name: payload.name,
      slug: payload.slug,
      parent_id: payload.parentId ?? null,
      description: payload.description ?? null,
      image_url: payload.imageUrl ?? null,
      sort_order: payload.sortOrder ?? 0,
      status: payload.status ?? 'active',
    }),
  });
  return fromApi(data.category);
}

export async function updateCategory(
  id: string,
  payload: CategoryUpdatePayload,
): Promise<Category> {
  const body: Record<string, unknown> = {};
  if (payload.name !== undefined) body.name = payload.name;
  if (payload.slug !== undefined) body.slug = payload.slug;
  if (payload.parentId !== undefined) body.parent_id = payload.parentId;
  if (payload.description !== undefined) body.description = payload.description;
  if (payload.imageUrl !== undefined) body.image_url = payload.imageUrl;
  if (payload.sortOrder !== undefined) body.sort_order = payload.sortOrder;
  if (payload.status !== undefined) body.status = payload.status;

  const data = await apiFetch<{ category: CategoryApi }>(
    `/admin/categories/${id}`,
    {
      method: 'PATCH',
      body: JSON.stringify(body),
    },
  );
  return fromApi(data.category);
}

export async function deleteCategory(id: string): Promise<void> {
  await apiFetch<void>(`/admin/categories/${id}`, { method: 'DELETE' });
}
