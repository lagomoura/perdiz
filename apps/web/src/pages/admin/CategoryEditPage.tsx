import { useEffect, useMemo, useRef, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';

import { Button } from '@/components/ui/Button';
import { FormMessage } from '@/components/ui/FormMessage';
import { Input } from '@/components/ui/Input';
import { Label } from '@/components/ui/Label';
import {
  buildTree,
  descendantIds,
  flattenTree,
  useCategories,
  useCategory,
  useCreateCategory,
  useUpdateCategory,
} from '@/features/admin/categories';
import { getErrorMessage } from '@/lib/errors';
import { slugify } from '@/lib/slug';
import type { CategoryStatus } from '@/types/catalog';

interface FormState {
  name: string;
  slug: string;
  slugTouched: boolean;
  parentId: string;
  description: string;
  imageUrl: string;
  sortOrder: number;
  status: CategoryStatus;
}

const EMPTY: FormState = {
  name: '',
  slug: '',
  slugTouched: false,
  parentId: '',
  description: '',
  imageUrl: '',
  sortOrder: 0,
  status: 'active',
};

export function CategoryEditPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const isEdit = !!id;

  const { data: categories } = useCategories();
  const { data: existing, isLoading: loadingExisting } = useCategory(id);
  const create = useCreateCategory();
  const update = useUpdateCategory();

  const [form, setForm] = useState<FormState>(EMPTY);
  const [serverError, setServerError] = useState<string | null>(null);
  const loaded = useRef(false);

  useEffect(() => {
    if (!isEdit || !existing || loaded.current) return;
    loaded.current = true;
    setForm({
      name: existing.name,
      slug: existing.slug,
      slugTouched: true,
      parentId: existing.parentId ?? '',
      description: existing.description ?? '',
      imageUrl: existing.imageUrl ?? '',
      sortOrder: existing.sortOrder,
      status: existing.status,
    });
  }, [existing, isEdit]);

  const parentOptions = useMemo(() => {
    if (!categories) return [];
    const tree = buildTree(categories);
    const forbidden = id ? descendantIds(tree, id) : new Set<string>();
    return flattenTree(tree)
      .filter((c) => c.id !== id && !forbidden.has(c.id))
      .map((c) => ({
        id: c.id,
        label: `${'— '.repeat(c.depth)}${c.name}`,
      }));
  }, [categories, id]);

  function setName(name: string) {
    setForm((f) => ({
      ...f,
      name,
      slug: f.slugTouched ? f.slug : slugify(name),
    }));
  }

  function setSlug(slug: string) {
    setForm((f) => ({ ...f, slug, slugTouched: true }));
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setServerError(null);
    const payload = {
      name: form.name.trim(),
      slug: form.slug.trim() || slugify(form.name),
      parentId: form.parentId || null,
      description: form.description.trim() || null,
      imageUrl: form.imageUrl.trim() || null,
      sortOrder: Number(form.sortOrder) || 0,
      status: form.status,
    };

    try {
      if (isEdit && id) {
        await update.mutateAsync({ id, payload });
      } else {
        await create.mutateAsync(payload);
      }
      navigate('/admin/categorias');
    } catch (e) {
      const code = (e as { code?: string })?.code ?? 'HTTP_ERROR';
      const msg =
        (e as { message?: string })?.message ?? 'Error al guardar la categoría.';
      setServerError(getErrorMessage(code, msg));
    }
  }

  const pending = create.isPending || update.isPending;
  const showLoading = isEdit && loadingExisting;

  return (
    <div className="mx-auto max-w-2xl">
      <h1 className="mb-6 font-display text-2xl font-bold text-neutral-900">
        {isEdit ? 'Editar categoría' : 'Nueva categoría'}
      </h1>

      {showLoading ? (
        <p className="text-sm text-neutral-500">Cargando…</p>
      ) : (
        <form
          onSubmit={handleSubmit}
          noValidate
          className="space-y-5 rounded-xl border border-neutral-200 bg-neutral-50 p-6"
        >
          <div>
            <Label htmlFor="name">Nombre</Label>
            <Input
              id="name"
              type="text"
              required
              value={form.name}
              onChange={(e) => setName(e.target.value)}
              className="mt-1"
            />
          </div>

          <div>
            <Label htmlFor="slug">Slug</Label>
            <Input
              id="slug"
              type="text"
              required
              value={form.slug}
              onChange={(e) => setSlug(e.target.value)}
              className="mt-1 font-mono"
            />
            <p className="mt-1 text-xs text-neutral-500">
              Se autogenera del nombre. Podés editarlo.
            </p>
          </div>

          <div>
            <Label htmlFor="parent">Categoría padre</Label>
            <select
              id="parent"
              value={form.parentId}
              onChange={(e) =>
                setForm((f) => ({ ...f, parentId: e.target.value }))
              }
              className="mt-1 w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm"
            >
              <option value="">— Sin padre (nivel raíz) —</option>
              {parentOptions.map((o) => (
                <option key={o.id} value={o.id}>
                  {o.label}
                </option>
              ))}
            </select>
          </div>

          <div>
            <Label htmlFor="description">Descripción</Label>
            <textarea
              id="description"
              rows={3}
              value={form.description}
              onChange={(e) =>
                setForm((f) => ({ ...f, description: e.target.value }))
              }
              className="mt-1 w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm"
            />
          </div>

          <div>
            <Label htmlFor="imageUrl">Imagen (URL)</Label>
            <Input
              id="imageUrl"
              type="url"
              placeholder="https://..."
              value={form.imageUrl}
              onChange={(e) =>
                setForm((f) => ({ ...f, imageUrl: e.target.value }))
              }
              className="mt-1"
            />
            <p className="mt-1 text-xs text-neutral-500">
              Por ahora podés pegar una URL. El upload inline llega en el próximo
              PR.
            </p>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <Label htmlFor="sortOrder">Orden</Label>
              <Input
                id="sortOrder"
                type="number"
                min={0}
                value={form.sortOrder}
                onChange={(e) =>
                  setForm((f) => ({
                    ...f,
                    sortOrder: Number(e.target.value) || 0,
                  }))
                }
                className="mt-1"
              />
            </div>
            <div>
              <Label htmlFor="status">Estado</Label>
              <select
                id="status"
                value={form.status}
                onChange={(e) =>
                  setForm((f) => ({
                    ...f,
                    status: e.target.value as CategoryStatus,
                  }))
                }
                className="mt-1 w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm"
              >
                <option value="active">Activa</option>
                <option value="archived">Archivada</option>
              </select>
            </div>
          </div>

          {serverError && <FormMessage message={serverError} />}

          <div className="flex items-center justify-end gap-3">
            <Button
              type="button"
              variant="ghost"
              onClick={() => navigate('/admin/categorias')}
            >
              Cancelar
            </Button>
            <Button type="submit" loading={pending}>
              {pending
                ? 'Guardando…'
                : isEdit
                  ? 'Guardar cambios'
                  : 'Crear categoría'}
            </Button>
          </div>
        </form>
      )}
    </div>
  );
}
