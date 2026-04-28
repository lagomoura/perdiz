import { useEffect, useState } from 'react';
import { useSearchParams } from 'react-router-dom';

import { ProductCard } from '@/components/catalog/ProductCard';
import { Spinner } from '@/components/feedback/Spinner';
import {
  usePublicCategories,
  usePublicProducts,
} from '@/features/catalog/hooks';
import type { Availability, CatalogSort } from '@/types/catalog';

const SORT_OPTIONS: { value: CatalogSort; label: string }[] = [
  { value: 'newest', label: 'Más nuevos' },
  { value: 'price_asc', label: 'Precio ↑' },
  { value: 'price_desc', label: 'Precio ↓' },
  { value: 'relevance', label: 'Relevancia' },
];

export function CatalogPage() {
  const [searchParams, setSearchParams] = useSearchParams();

  const q = searchParams.get('q') ?? '';
  const category = searchParams.get('category') ?? '';
  const availability = (searchParams.get('availability') ?? '') as
    | Availability
    | '';
  const sort = (searchParams.get('sort') ?? 'newest') as CatalogSort;

  const [searchInput, setSearchInput] = useState(q);
  useEffect(() => setSearchInput(q), [q]);

  const { data: categories } = usePublicCategories();
  const { data: listing, isLoading, error } = usePublicProducts({
    q: q || undefined,
    category: category || undefined,
    availability: availability || undefined,
    sort,
    limit: 24,
  });

  function updateParam(key: string, value: string) {
    const next = new URLSearchParams(searchParams);
    if (value) next.set(key, value);
    else next.delete(key);
    setSearchParams(next, { replace: true });
  }

  function onSearchSubmit(e: React.FormEvent) {
    e.preventDefault();
    updateParam('q', searchInput.trim());
  }

  const products = listing?.data ?? [];

  return (
    <div className="mx-auto max-w-7xl px-4 py-10 md:px-6">
      <h1 className="font-display text-3xl font-bold text-neutral-900 md:text-4xl">
        Catálogo
      </h1>
      <p className="mt-2 text-neutral-600">
        Ideas impresas en 3D listas para llevar o bajo pedido.
      </p>

      <div className="mt-8 grid gap-8 lg:grid-cols-[240px_1fr]">
        {/* Sidebar filtros */}
        <aside className="space-y-6">
          <form onSubmit={onSearchSubmit}>
            <label
              htmlFor="q"
              className="text-xs font-semibold uppercase tracking-wider text-neutral-500"
            >
              Buscar
            </label>
            <input
              id="q"
              type="search"
              value={searchInput}
              onChange={(e) => setSearchInput(e.target.value)}
              placeholder="Nombre, descripción…"
              className="mt-2 w-full rounded-lg border border-neutral-200 bg-neutral-50 px-3 py-2 text-sm focus:border-brand-orange-500 focus:outline-none"
            />
          </form>

          <div>
            <p className="text-xs font-semibold uppercase tracking-wider text-neutral-500">
              Categoría
            </p>
            <ul className="mt-2 space-y-1">
              <li>
                <button
                  type="button"
                  onClick={() => updateParam('category', '')}
                  className={`w-full rounded-md px-2 py-1.5 text-left text-sm transition-colors ${
                    !category
                      ? 'bg-brand-orange-500/15 text-brand-orange-500'
                      : 'text-neutral-600 hover:bg-neutral-100'
                  }`}
                >
                  Todas
                </button>
              </li>
              {(categories ?? []).map((c) => (
                <li key={c.id}>
                  <button
                    type="button"
                    onClick={() => updateParam('category', c.slug)}
                    className={`w-full rounded-md px-2 py-1.5 text-left text-sm transition-colors ${
                      category === c.slug
                        ? 'bg-brand-orange-500/15 text-brand-orange-500'
                        : 'text-neutral-600 hover:bg-neutral-100'
                    }`}
                  >
                    {c.name}
                  </button>
                </li>
              ))}
            </ul>
          </div>

          <div>
            <p className="text-xs font-semibold uppercase tracking-wider text-neutral-500">
              Disponibilidad
            </p>
            <div className="mt-2 space-y-1">
              {(
                [
                  { value: '', label: 'Todas' },
                  { value: 'in_stock', label: 'En stock' },
                  { value: 'on_demand', label: 'Bajo pedido' },
                ] as const
              ).map((opt) => (
                <button
                  key={opt.value || 'all'}
                  type="button"
                  onClick={() => updateParam('availability', opt.value)}
                  className={`w-full rounded-md px-2 py-1.5 text-left text-sm transition-colors ${
                    availability === opt.value
                      ? 'bg-brand-orange-500/15 text-brand-orange-500'
                      : 'text-neutral-600 hover:bg-neutral-100'
                  }`}
                >
                  {opt.label}
                </button>
              ))}
            </div>
          </div>
        </aside>

        {/* Grilla */}
        <section>
          <div className="mb-4 flex items-center justify-between">
            <p className="text-sm text-neutral-500">
              {listing
                ? `${listing.pagination.count} ${listing.pagination.count === 1 ? 'producto' : 'productos'}`
                : '…'}
            </p>
            <select
              value={sort}
              onChange={(e) => updateParam('sort', e.target.value)}
              className="rounded-lg border border-neutral-200 bg-neutral-50 px-3 py-1 text-sm"
            >
              {SORT_OPTIONS.map((s) => (
                <option key={s.value} value={s.value}>
                  Ordenar: {s.label}
                </option>
              ))}
            </select>
          </div>

          {isLoading && (
            <div className="flex justify-center py-16">
              <Spinner />
            </div>
          )}
          {error && (
            <p className="rounded-lg border border-error-500 bg-red-50 p-4 text-sm text-error-500">
              Error al cargar el catálogo.
            </p>
          )}
          {!isLoading && !error && products.length === 0 && (
            <div className="rounded-xl border border-dashed border-neutral-200 p-12 text-center text-neutral-500">
              No encontramos productos con esos filtros.
            </div>
          )}
          {products.length > 0 && (
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
              {products.map((p) => (
                <ProductCard key={p.id} product={p} />
              ))}
            </div>
          )}
        </section>
      </div>
    </div>
  );
}
