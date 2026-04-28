import { useEffect, useMemo, useRef, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';

import { Button } from '@/components/ui/Button';
import { FormMessage } from '@/components/ui/FormMessage';
import { Input } from '@/components/ui/Input';
import { Label } from '@/components/ui/Label';
import {
  buildTree,
  flattenTree,
  useCategories,
} from '@/features/admin/categories';
import {
  useCreateProduct,
  useProduct,
  useUpdateProduct,
} from '@/features/admin/products';
import { getErrorMessage } from '@/lib/errors';
import { slugify } from '@/lib/slug';
import type {
  ProductCreatePayload,
  ProductStatus,
  StockMode,
} from '@/types/catalog';

import { ProductImagesPanel } from './ProductImagesPanel';

interface FormState {
  name: string;
  slug: string;
  slugTouched: boolean;
  sku: string;
  categoryId: string;
  description: string;
  basePricePesos: string; // as-entered string; parse to cents on submit
  stockMode: StockMode;
  stockQuantity: string;
  leadTimeDays: string;
  weightGrams: string;
  dimensionsText: string; // "W x D x H" in mm
  tags: string; // comma separated
  status: ProductStatus;
}

const EMPTY: FormState = {
  name: '',
  slug: '',
  slugTouched: false,
  sku: '',
  categoryId: '',
  description: '',
  basePricePesos: '',
  stockMode: 'stocked',
  stockQuantity: '1',
  leadTimeDays: '',
  weightGrams: '',
  dimensionsText: '',
  tags: '',
  status: 'draft',
};

function parseDimensions(text: string): number[] | null {
  const trimmed = text.trim();
  if (!trimmed) return null;
  const parts = trimmed
    .split(/[x×,]/i)
    .map((s) => Number(s.trim()))
    .filter((n) => Number.isFinite(n) && n >= 0);
  return parts.length ? parts : null;
}

function pesosToCents(input: string): number {
  const normalized = input.replace(/\./g, '').replace(',', '.').trim();
  const num = Number(normalized);
  if (!Number.isFinite(num) || num < 0) return 0;
  return Math.round(num * 100);
}

function centsToPesosInput(cents: number): string {
  if (!Number.isFinite(cents) || cents === 0) return '';
  return (cents / 100).toFixed(2).replace('.', ',');
}

export function ProductEditPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const isEdit = !!id;

  const { data: existing, isLoading: loadingExisting } = useProduct(id);
  const { data: categories } = useCategories();
  const create = useCreateProduct();
  const update = useUpdateProduct();

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
      sku: existing.sku,
      categoryId: existing.categoryId,
      description: existing.description ?? '',
      basePricePesos: centsToPesosInput(existing.basePriceCents),
      stockMode: existing.stockMode,
      stockQuantity: existing.stockQuantity?.toString() ?? '',
      leadTimeDays: existing.leadTimeDays?.toString() ?? '',
      weightGrams: existing.weightGrams?.toString() ?? '',
      dimensionsText: (existing.dimensionsMm ?? []).join(' x '),
      tags: (existing.tags ?? []).join(', '),
      status: existing.status,
    });
  }, [existing, isEdit]);

  const categoryOptions = useMemo(() => {
    if (!categories) return [];
    return flattenTree(buildTree(categories))
      .filter((c) => c.status === 'active')
      .map((c) => ({
        id: c.id,
        label: `${'— '.repeat(c.depth)}${c.name}`,
      }));
  }, [categories]);

  function setName(name: string) {
    setForm((f) => ({
      ...f,
      name,
      slug: f.slugTouched ? f.slug : slugify(name),
    }));
  }

  function buildPayload(): ProductCreatePayload {
    const tags = form.tags
      .split(',')
      .map((t) => t.trim())
      .filter(Boolean);
    const dims = parseDimensions(form.dimensionsText);
    const stockMode = form.stockMode;
    return {
      categoryId: form.categoryId,
      name: form.name.trim(),
      slug: form.slug.trim() || slugify(form.name),
      description: form.description.trim() || null,
      basePriceCents: pesosToCents(form.basePricePesos),
      stockMode,
      stockQuantity:
        stockMode === 'stocked' ? Number(form.stockQuantity) || 0 : null,
      leadTimeDays:
        stockMode === 'print_on_demand'
          ? Number(form.leadTimeDays) || 1
          : null,
      weightGrams: form.weightGrams ? Number(form.weightGrams) : null,
      dimensionsMm: dims,
      sku: form.sku.trim(),
      tags,
      status: form.status,
    };
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setServerError(null);

    if (!form.categoryId) {
      setServerError('Elegí una categoría.');
      return;
    }

    const payload = buildPayload();

    try {
      if (isEdit && id) {
        await update.mutateAsync({ id, payload });
      } else {
        const created = await create.mutateAsync(payload);
        navigate(`/admin/productos/${created.id}`, { replace: true });
        return;
      }
    } catch (err) {
      const code = (err as { code?: string })?.code ?? 'HTTP_ERROR';
      const msg =
        (err as { message?: string })?.message ?? 'Error al guardar el producto.';
      setServerError(getErrorMessage(code, msg));
    }
  }

  const pending = create.isPending || update.isPending;
  const showLoading = isEdit && loadingExisting;

  return (
    <div className="mx-auto max-w-3xl space-y-6">
      <h1 className="font-display text-2xl font-bold text-neutral-900">
        {isEdit ? 'Editar producto' : 'Nuevo producto'}
      </h1>

      {showLoading ? (
        <p className="text-sm text-neutral-500">Cargando…</p>
      ) : (
        <form
          onSubmit={handleSubmit}
          noValidate
          className="space-y-5 rounded-xl border border-neutral-200 bg-neutral-50 p-6"
        >
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
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
              <Label htmlFor="sku">SKU</Label>
              <Input
                id="sku"
                type="text"
                required
                value={form.sku}
                onChange={(e) =>
                  setForm((f) => ({ ...f, sku: e.target.value }))
                }
                className="mt-1 font-mono"
              />
            </div>
          </div>

          <div>
            <Label htmlFor="slug">Slug</Label>
            <Input
              id="slug"
              type="text"
              required
              value={form.slug}
              onChange={(e) =>
                setForm((f) => ({
                  ...f,
                  slug: e.target.value,
                  slugTouched: true,
                }))
              }
              className="mt-1 font-mono"
            />
            <p className="mt-1 text-xs text-neutral-500">
              Se autogenera del nombre. Podés editarlo.
            </p>
          </div>

          <div>
            <Label htmlFor="category">Categoría</Label>
            <select
              id="category"
              required
              value={form.categoryId}
              onChange={(e) =>
                setForm((f) => ({ ...f, categoryId: e.target.value }))
              }
              className="mt-1 w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm"
            >
              <option value="">— Elegí una categoría —</option>
              {categoryOptions.map((o) => (
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
              rows={4}
              value={form.description}
              onChange={(e) =>
                setForm((f) => ({ ...f, description: e.target.value }))
              }
              className="mt-1 w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm"
              placeholder="Qué es, para qué sirve, detalles importantes…"
            />
          </div>

          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <div>
              <Label htmlFor="price">Precio base (ARS)</Label>
              <Input
                id="price"
                type="text"
                inputMode="decimal"
                required
                placeholder="15.000,00"
                value={form.basePricePesos}
                onChange={(e) =>
                  setForm((f) => ({ ...f, basePricePesos: e.target.value }))
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
                    status: e.target.value as ProductStatus,
                  }))
                }
                className="mt-1 w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm"
              >
                <option value="draft">Borrador</option>
                <option value="active">Activo</option>
                <option value="archived">Archivado</option>
              </select>
            </div>
          </div>

          <div>
            <Label>Disponibilidad</Label>
            <div className="mt-2 flex gap-3">
              {(['stocked', 'print_on_demand'] as const).map((m) => (
                <label
                  key={m}
                  className={`flex-1 cursor-pointer rounded-lg border px-4 py-3 text-sm ${
                    form.stockMode === m
                      ? 'border-brand-orange-500 bg-brand-orange-500/15'
                      : 'border-neutral-200 bg-neutral-50'
                  }`}
                >
                  <input
                    type="radio"
                    name="stockMode"
                    value={m}
                    checked={form.stockMode === m}
                    onChange={() =>
                      setForm((f) => ({ ...f, stockMode: m }))
                    }
                    className="mr-2"
                  />
                  {m === 'stocked' ? 'En stock' : 'Bajo pedido'}
                </label>
              ))}
            </div>
          </div>

          {form.stockMode === 'stocked' ? (
            <div>
              <Label htmlFor="stock">Cantidad en stock</Label>
              <Input
                id="stock"
                type="number"
                min={0}
                value={form.stockQuantity}
                onChange={(e) =>
                  setForm((f) => ({ ...f, stockQuantity: e.target.value }))
                }
                className="mt-1"
              />
            </div>
          ) : (
            <div>
              <Label htmlFor="lead">Días de espera (lead time)</Label>
              <Input
                id="lead"
                type="number"
                min={1}
                value={form.leadTimeDays}
                onChange={(e) =>
                  setForm((f) => ({ ...f, leadTimeDays: e.target.value }))
                }
                className="mt-1"
                placeholder="p. ej. 7"
              />
            </div>
          )}

          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <div>
              <Label htmlFor="weight">Peso (gramos)</Label>
              <Input
                id="weight"
                type="number"
                min={0}
                value={form.weightGrams}
                onChange={(e) =>
                  setForm((f) => ({ ...f, weightGrams: e.target.value }))
                }
                className="mt-1"
                placeholder="Opcional"
              />
            </div>
            <div>
              <Label htmlFor="dims">Dimensiones (mm)</Label>
              <Input
                id="dims"
                type="text"
                value={form.dimensionsText}
                onChange={(e) =>
                  setForm((f) => ({ ...f, dimensionsText: e.target.value }))
                }
                className="mt-1"
                placeholder="100 x 50 x 30"
              />
            </div>
          </div>

          <div>
            <Label htmlFor="tags">Tags</Label>
            <Input
              id="tags"
              type="text"
              value={form.tags}
              onChange={(e) =>
                setForm((f) => ({ ...f, tags: e.target.value }))
              }
              className="mt-1"
              placeholder="separadas, por, comas"
            />
          </div>

          {serverError && <FormMessage message={serverError} />}

          <div className="flex items-center justify-end gap-3">
            <Button
              type="button"
              variant="ghost"
              onClick={() => navigate('/admin/productos')}
            >
              Cancelar
            </Button>
            <Button type="submit" loading={pending}>
              {pending
                ? 'Guardando…'
                : isEdit
                  ? 'Guardar cambios'
                  : 'Crear producto'}
            </Button>
          </div>
        </form>
      )}

      {isEdit && id && <ProductImagesPanel productId={id} />}
    </div>
  );
}
