import { useMemo, useState } from 'react';
import { Link } from 'react-router-dom';

import { Button } from '@/components/ui/Button';
import {
  buildTree,
  flattenTree,
  useCategories,
} from '@/features/admin/categories';
import { useDeleteProduct, useProducts } from '@/features/admin/products';
import { getErrorMessage } from '@/lib/errors';
import type { ProductStatus } from '@/types/catalog';

function formatAR(cents: number): string {
  const pesos = cents / 100;
  return pesos.toLocaleString('es-AR', {
    style: 'currency',
    currency: 'ARS',
    minimumFractionDigits: 2,
  });
}

export function ProductsListPage() {
  const [status, setStatus] = useState<ProductStatus | 'all'>('all');
  const [categoryId, setCategoryId] = useState<string>('');
  const { data: listing, isLoading, error } = useProducts({
    status: status === 'all' ? undefined : status,
    categoryId: categoryId || undefined,
  });
  const { data: categories } = useCategories();
  const del = useDeleteProduct();
  const [deleteError, setDeleteError] = useState<string | null>(null);

  const categoriesById = useMemo(() => {
    const m = new Map<string, string>();
    (categories ?? []).forEach((c) => m.set(c.id, c.name));
    return m;
  }, [categories]);

  const categoryOptions = useMemo(() => {
    if (!categories) return [];
    return flattenTree(buildTree(categories)).map((c) => ({
      id: c.id,
      label: `${'— '.repeat(c.depth)}${c.name}`,
    }));
  }, [categories]);

  async function handleDelete(id: string, name: string) {
    setDeleteError(null);
    if (!confirm(`¿Eliminar "${name}"? No se puede deshacer.`)) return;
    try {
      await del.mutateAsync(id);
    } catch (e) {
      const code = (e as { code?: string })?.code ?? 'HTTP_ERROR';
      const msg = (e as { message?: string })?.message ?? 'Error al eliminar.';
      setDeleteError(getErrorMessage(code, msg));
    }
  }

  const products = listing?.data ?? [];

  return (
    <div className="mx-auto max-w-6xl">
      <div className="mb-6 flex items-center justify-between">
        <h1 className="font-display text-2xl font-bold text-brand-graphite-900">
          Productos
        </h1>
        <Link to="/admin/productos/nuevo">
          <Button size="md">+ Nuevo producto</Button>
        </Link>
      </div>

      <div className="mb-4 flex flex-wrap items-center gap-3 text-sm">
        <span className="text-neutral-600">Estado:</span>
        {(['all', 'draft', 'active', 'archived'] as const).map((s) => (
          <button
            key={s}
            type="button"
            onClick={() => setStatus(s)}
            className={`rounded-full px-3 py-1 ${
              status === s
                ? 'bg-brand-graphite-900 text-white'
                : 'bg-white text-neutral-700 hover:bg-neutral-100'
            }`}
          >
            {s === 'all'
              ? 'Todos'
              : s === 'draft'
                ? 'Borradores'
                : s === 'active'
                  ? 'Activos'
                  : 'Archivados'}
          </button>
        ))}
        <span className="ml-4 text-neutral-600">Categoría:</span>
        <select
          value={categoryId}
          onChange={(e) => setCategoryId(e.target.value)}
          className="rounded-lg border border-neutral-300 bg-white px-3 py-1 text-sm"
        >
          <option value="">Todas</option>
          {categoryOptions.map((o) => (
            <option key={o.id} value={o.id}>
              {o.label}
            </option>
          ))}
        </select>
      </div>

      {deleteError && (
        <div className="mb-4 rounded-lg border border-error-500 bg-red-50 p-3 text-sm text-error-500">
          {deleteError}
        </div>
      )}

      <div className="overflow-hidden rounded-xl border border-neutral-200 bg-white">
        {isLoading && <p className="p-6 text-sm text-neutral-500">Cargando…</p>}
        {error && (
          <p className="p-6 text-sm text-error-500">
            Error al cargar productos.
          </p>
        )}
        {!isLoading && !error && products.length === 0 && (
          <p className="p-6 text-center text-sm text-neutral-500">
            No hay productos todavía. Creá el primero.
          </p>
        )}
        {products.length > 0 && (
          <table className="w-full text-left text-sm">
            <thead className="border-b border-neutral-200 bg-neutral-50 text-xs uppercase tracking-wider text-neutral-500">
              <tr>
                <th className="px-4 py-3">Nombre</th>
                <th className="px-4 py-3">Categoría</th>
                <th className="px-4 py-3">SKU</th>
                <th className="px-4 py-3 text-right">Precio</th>
                <th className="px-4 py-3">Stock</th>
                <th className="px-4 py-3">Estado</th>
                <th className="px-4 py-3 text-right">Acciones</th>
              </tr>
            </thead>
            <tbody>
              {products.map((p) => (
                <tr
                  key={p.id}
                  className="border-b border-neutral-100 last:border-b-0"
                >
                  <td className="px-4 py-3">
                    <div className="font-medium text-brand-graphite-900">
                      {p.name}
                    </div>
                    <div className="text-xs text-neutral-500">{p.slug}</div>
                  </td>
                  <td className="px-4 py-3 text-neutral-600">
                    {categoriesById.get(p.categoryId) ?? '—'}
                  </td>
                  <td className="px-4 py-3 font-mono text-xs text-neutral-600">
                    {p.sku}
                  </td>
                  <td className="px-4 py-3 text-right text-neutral-800">
                    {formatAR(p.basePriceCents)}
                  </td>
                  <td className="px-4 py-3 text-neutral-600">
                    {p.stockMode === 'stocked'
                      ? `${p.stockQuantity ?? 0} uds.`
                      : `Bajo pedido${p.leadTimeDays ? ` · ${p.leadTimeDays}d` : ''}`}
                  </td>
                  <td className="px-4 py-3">
                    <StatusBadge status={p.status} />
                  </td>
                  <td className="px-4 py-3 text-right whitespace-nowrap">
                    <Link
                      to={`/admin/productos/${p.id}`}
                      className="mr-3 text-sm text-brand-orange-500 hover:text-brand-orange-600"
                    >
                      Editar
                    </Link>
                    <button
                      type="button"
                      onClick={() => handleDelete(p.id, p.name)}
                      className="text-sm text-error-500 hover:opacity-80"
                    >
                      Eliminar
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {listing && listing.count > products.length && (
        <p className="mt-4 text-sm text-neutral-500">
          Mostrando {products.length} de {listing.count}.
        </p>
      )}
    </div>
  );
}

function StatusBadge({ status }: { status: ProductStatus }) {
  const map: Record<ProductStatus, { label: string; cls: string }> = {
    draft: { label: 'Borrador', cls: 'bg-neutral-100 text-neutral-700' },
    active: { label: 'Activo', cls: 'bg-green-100 text-green-800' },
    archived: { label: 'Archivado', cls: 'bg-neutral-100 text-neutral-500' },
  };
  const s = map[status];
  return (
    <span
      className={`inline-block rounded-full px-2 py-0.5 text-xs font-medium ${s.cls}`}
    >
      {s.label}
    </span>
  );
}
