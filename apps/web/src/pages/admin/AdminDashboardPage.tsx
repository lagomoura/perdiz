import { Link } from 'react-router-dom';

import { useCategories } from '@/features/admin/categories';
import { useProducts } from '@/features/admin/products';

export function AdminDashboardPage() {
  const { data: categories, isLoading: loadingCats } = useCategories();
  const { data: products, isLoading: loadingProds } = useProducts({});

  return (
    <div className="mx-auto max-w-4xl">
      <h1 className="mb-6 font-display text-2xl font-bold text-brand-graphite-900">
        Dashboard
      </h1>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
        <Link
          to="/admin/categorias"
          className="rounded-xl border border-neutral-200 bg-white p-6 transition-shadow hover:shadow-md"
        >
          <p className="text-xs font-semibold uppercase tracking-wider text-neutral-500">
            Categorías
          </p>
          <p className="mt-2 text-3xl font-bold text-brand-graphite-900">
            {loadingCats ? '…' : (categories?.length ?? 0)}
          </p>
          <p className="mt-2 text-sm text-neutral-600">
            Gestionar categorías y sub-categorías.
          </p>
        </Link>

        <Link
          to="/admin/productos"
          className="rounded-xl border border-neutral-200 bg-white p-6 transition-shadow hover:shadow-md"
        >
          <p className="text-xs font-semibold uppercase tracking-wider text-neutral-500">
            Productos
          </p>
          <p className="mt-2 text-3xl font-bold text-brand-graphite-900">
            {loadingProds ? '…' : (products?.count ?? 0)}
          </p>
          <p className="mt-2 text-sm text-neutral-600">
            Crear y gestionar el catálogo.
          </p>
        </Link>
      </div>
    </div>
  );
}
