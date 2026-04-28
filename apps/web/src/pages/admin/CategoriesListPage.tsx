import { useMemo, useState } from 'react';
import { Link } from 'react-router-dom';

import { Button } from '@/components/ui/Button';
import {
  buildTree,
  flattenTree,
  useCategories,
  useDeleteCategory,
} from '@/features/admin/categories';
import { getErrorMessage } from '@/lib/errors';
import type { CategoryStatus } from '@/types/catalog';

export function CategoriesListPage() {
  const [statusFilter, setStatusFilter] = useState<CategoryStatus | 'all'>(
    'all',
  );
  const { data, isLoading, error } = useCategories(
    statusFilter === 'all' ? undefined : statusFilter,
  );
  const del = useDeleteCategory();
  const [deleteError, setDeleteError] = useState<string | null>(null);

  const flat = useMemo(() => {
    if (!data) return [];
    return flattenTree(buildTree(data));
  }, [data]);

  async function handleDelete(id: string, name: string) {
    setDeleteError(null);
    if (!confirm(`¿Eliminar la categoría "${name}"? No se puede deshacer.`)) {
      return;
    }
    try {
      await del.mutateAsync(id);
    } catch (e) {
      const code = (e as { code?: string })?.code ?? 'HTTP_ERROR';
      const msg = (e as { message?: string })?.message ?? 'Error al eliminar.';
      setDeleteError(getErrorMessage(code, msg));
    }
  }

  return (
    <div className="mx-auto max-w-5xl">
      <div className="mb-6 flex items-center justify-between">
        <h1 className="font-display text-2xl font-bold text-neutral-900">
          Categorías
        </h1>
        <div className="flex gap-2">
          <Link to="/admin/categorias/importar">
            <Button size="md" variant="ghost">
              Importar CSV
            </Button>
          </Link>
          <Link to="/admin/categorias/nueva">
            <Button size="md">+ Nueva categoría</Button>
          </Link>
        </div>
      </div>

      <div className="mb-4 flex items-center gap-2 text-sm">
        <span className="text-neutral-600">Filtrar:</span>
        {(['all', 'active', 'archived'] as const).map((s) => (
          <button
            key={s}
            type="button"
            onClick={() => setStatusFilter(s)}
            className={`rounded-full px-3 py-1 ${
              statusFilter === s
                ? 'bg-brand-graphite-900 text-white'
                : 'bg-neutral-50 text-neutral-600 hover:bg-neutral-100'
            }`}
          >
            {s === 'all' ? 'Todas' : s === 'active' ? 'Activas' : 'Archivadas'}
          </button>
        ))}
      </div>

      {deleteError && (
        <div className="mb-4 rounded-lg border border-error-500 bg-red-50 p-3 text-sm text-error-500">
          {deleteError}
        </div>
      )}

      <div className="overflow-hidden rounded-xl border border-neutral-200 bg-neutral-50">
        {isLoading && (
          <p className="p-6 text-sm text-neutral-500">Cargando…</p>
        )}
        {error && (
          <p className="p-6 text-sm text-error-500">
            Error al cargar categorías.
          </p>
        )}
        {!isLoading && !error && flat.length === 0 && (
          <p className="p-6 text-center text-sm text-neutral-500">
            No hay categorías todavía. Creá la primera.
          </p>
        )}
        {flat.length > 0 && (
          <table className="w-full text-left text-sm">
            <thead className="border-b border-neutral-200 bg-neutral-50 text-xs uppercase tracking-wider text-neutral-500">
              <tr>
                <th className="px-4 py-3">Nombre</th>
                <th className="px-4 py-3">Slug</th>
                <th className="px-4 py-3">Orden</th>
                <th className="px-4 py-3">Estado</th>
                <th className="px-4 py-3 text-right">Acciones</th>
              </tr>
            </thead>
            <tbody>
              {flat.map((c) => (
                <tr
                  key={c.id}
                  className="border-b border-neutral-100 last:border-b-0"
                >
                  <td className="px-4 py-3">
                    <span style={{ paddingLeft: `${c.depth * 20}px` }}>
                      {c.depth > 0 && (
                        <span className="mr-2 text-neutral-400">└</span>
                      )}
                      <span className="font-medium text-neutral-900">
                        {c.name}
                      </span>
                    </span>
                  </td>
                  <td className="px-4 py-3 text-neutral-600">{c.slug}</td>
                  <td className="px-4 py-3 text-neutral-600">{c.sortOrder}</td>
                  <td className="px-4 py-3">
                    <span
                      className={`inline-block rounded-full px-2 py-0.5 text-xs font-medium ${
                        c.status === 'active'
                          ? 'bg-green-100 text-green-800'
                          : 'bg-neutral-100 text-neutral-600'
                      }`}
                    >
                      {c.status === 'active' ? 'Activa' : 'Archivada'}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-right">
                    <Link
                      to={`/admin/categorias/${c.id}`}
                      className="mr-3 text-sm text-brand-orange-500 hover:text-brand-orange-600"
                    >
                      Editar
                    </Link>
                    <button
                      type="button"
                      onClick={() => handleDelete(c.id, c.name)}
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
    </div>
  );
}
