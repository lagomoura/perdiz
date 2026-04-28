import { useState } from 'react';
import { Link, useParams } from 'react-router-dom';

import { Button } from '@/components/ui/Button';
import { Spinner } from '@/components/feedback/Spinner';
import { usePublicProduct } from '@/features/catalog/hooks';

function formatARS(cents: number): string {
  return (cents / 100).toLocaleString('es-AR', {
    style: 'currency',
    currency: 'ARS',
    minimumFractionDigits: 0,
  });
}

export function ProductDetailPage() {
  const { slug } = useParams<{ slug: string }>();
  const { data: product, isLoading, error } = usePublicProduct(slug);
  const [activeImage, setActiveImage] = useState(0);

  if (isLoading) {
    return (
      <div className="flex justify-center py-24">
        <Spinner />
      </div>
    );
  }

  if (error || !product) {
    return (
      <div className="mx-auto max-w-2xl px-4 py-24 text-center">
        <h1 className="text-xl font-semibold text-neutral-900">
          Producto no encontrado
        </h1>
        <p className="mt-2 text-neutral-600">
          Puede que haya sido removido o que la dirección sea incorrecta.
        </p>
        <Link
          to="/catalogo"
          className="mt-6 inline-block text-brand-orange-500 hover:text-brand-orange-600"
        >
          ← Volver al catálogo
        </Link>
      </div>
    );
  }

  const hasDiscount =
    product.discountedPriceCents !== null &&
    product.discountedPriceCents < product.basePriceCents;
  const mainImage = product.images[activeImage] ?? product.images[0];

  return (
    <div className="mx-auto max-w-6xl px-4 py-10 md:px-6">
      <nav className="mb-6 flex items-center gap-2 text-sm text-neutral-500">
        <Link to="/catalogo" className="hover:text-neutral-900">
          Catálogo
        </Link>
        <span>/</span>
        <Link
          to={`/catalogo?category=${product.category.slug}`}
          className="hover:text-neutral-900"
        >
          {product.category.name}
        </Link>
      </nav>

      <div className="grid gap-10 lg:grid-cols-2">
        {/* Galería */}
        <div>
          <div className="aspect-square overflow-hidden rounded-xl bg-neutral-100">
            {mainImage ? (
              <img
                src={mainImage.url}
                alt={mainImage.alt ?? product.name}
                className="h-full w-full object-cover"
              />
            ) : (
              <div className="flex h-full items-center justify-center text-sm text-neutral-400">
                Sin imágenes
              </div>
            )}
          </div>
          {product.images.length > 1 && (
            <div className="mt-3 grid grid-cols-5 gap-2">
              {product.images.map((img, idx) => (
                <button
                  key={idx}
                  type="button"
                  onClick={() => setActiveImage(idx)}
                  className={`aspect-square overflow-hidden rounded-lg border transition-all ${
                    activeImage === idx
                      ? 'border-brand-orange-500 ring-2 ring-brand-orange-200'
                      : 'border-neutral-200'
                  }`}
                >
                  <img
                    src={img.url}
                    alt={img.alt ?? ''}
                    className="h-full w-full object-cover"
                  />
                </button>
              ))}
            </div>
          )}
        </div>

        {/* Info */}
        <div>
          <h1 className="font-display text-3xl font-bold text-neutral-900 md:text-4xl">
            {product.name}
          </h1>

          <div className="mt-4 flex items-baseline gap-3">
            {hasDiscount ? (
              <>
                <span className="text-3xl font-bold text-brand-orange-500">
                  {formatARS(product.discountedPriceCents!)}
                </span>
                <span className="text-lg text-neutral-400 line-through">
                  {formatARS(product.basePriceCents)}
                </span>
              </>
            ) : (
              <span className="text-3xl font-bold text-neutral-900">
                {formatARS(product.basePriceCents)}
              </span>
            )}
          </div>

          <div className="mt-4 flex flex-wrap gap-2">
            <span
              className={`inline-block rounded-full px-3 py-1 text-xs font-medium ${
                product.availability === 'in_stock'
                  ? 'bg-green-100 text-green-800'
                  : 'bg-brand-graphite-900 text-white'
              }`}
            >
              {product.availability === 'in_stock'
                ? 'En stock'
                : product.leadTimeDays
                  ? `Bajo pedido · ${product.leadTimeDays} días`
                  : 'Bajo pedido'}
            </span>
            {product.customizable && (
              <span className="inline-block rounded-full bg-brand-orange-500/15 px-3 py-1 text-xs font-medium text-brand-orange-500">
                Personalizable
              </span>
            )}
          </div>

          {product.descriptionHtml && (
            <div
              className="prose prose-sm mt-6 max-w-none text-neutral-600"
              // eslint-disable-next-line react/no-danger
              dangerouslySetInnerHTML={{ __html: product.descriptionHtml }}
            />
          )}

          <div className="mt-8 flex flex-col gap-3 sm:flex-row">
            <Button
              size="lg"
              onClick={() =>
                alert(
                  'Carrito próximamente. Escribinos por email para hacer el pedido por ahora.',
                )
              }
            >
              Agregar al carrito
            </Button>
            <Link
              to="/catalogo"
              className="inline-flex items-center justify-center rounded-md border border-neutral-200 px-6 py-3 text-sm font-medium text-neutral-900 hover:bg-neutral-50"
            >
              Seguir mirando
            </Link>
          </div>

          <dl className="mt-8 divide-y divide-neutral-200 rounded-lg border border-neutral-200 text-sm">
            <div className="flex justify-between px-4 py-3">
              <dt className="text-neutral-500">Categoría</dt>
              <dd className="text-neutral-900">{product.category.name}</dd>
            </div>
            {product.stockMode === 'stocked' &&
              product.stockQuantity !== null && (
                <div className="flex justify-between px-4 py-3">
                  <dt className="text-neutral-500">Stock</dt>
                  <dd className="text-neutral-900">
                    {product.stockQuantity} unidades
                  </dd>
                </div>
              )}
            {product.stockMode === 'print_on_demand' &&
              product.leadTimeDays !== null && (
                <div className="flex justify-between px-4 py-3">
                  <dt className="text-neutral-500">Tiempo de entrega</dt>
                  <dd className="text-neutral-900">
                    {product.leadTimeDays} días
                  </dd>
                </div>
              )}
          </dl>
        </div>
      </div>
    </div>
  );
}
