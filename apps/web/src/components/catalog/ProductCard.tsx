import { Link } from 'react-router-dom';

import type { PublicProduct } from '@/types/catalog';

function formatARS(cents: number): string {
  return (cents / 100).toLocaleString('es-AR', {
    style: 'currency',
    currency: 'ARS',
    minimumFractionDigits: 0,
  });
}

export function ProductCard({ product }: { product: PublicProduct }) {
  const primaryImage = product.images[0];
  const hasDiscount =
    product.discountedPriceCents !== null &&
    product.discountedPriceCents < product.priceCents;

  return (
    <Link
      to={`/producto/${product.slug}`}
      className="group flex flex-col overflow-hidden rounded-xl border border-neutral-200 bg-neutral-50 transition-shadow hover:shadow-md"
    >
      <div className="relative aspect-square overflow-hidden bg-neutral-100">
        {primaryImage ? (
          <img
            src={primaryImage.url}
            alt={primaryImage.alt ?? product.name}
            loading="lazy"
            className="h-full w-full object-cover transition-transform duration-300 group-hover:scale-105"
          />
        ) : (
          <div className="flex h-full items-center justify-center text-xs text-neutral-400">
            Sin imagen
          </div>
        )}
        {product.availability === 'on_demand' && (
          <span className="absolute left-2 top-2 rounded-full bg-brand-graphite-900 px-2 py-0.5 text-xs font-medium text-white">
            Bajo pedido
          </span>
        )}
        {hasDiscount && (
          <span className="absolute right-2 top-2 rounded-full bg-brand-orange-500 px-2 py-0.5 text-xs font-medium text-white">
            Oferta
          </span>
        )}
      </div>

      <div className="flex flex-1 flex-col p-4">
        <p className="text-xs text-neutral-500">{product.category.name}</p>
        <h3 className="mt-1 line-clamp-2 font-medium text-neutral-900">
          {product.name}
        </h3>
        <div className="mt-auto pt-3">
          {hasDiscount ? (
            <div className="flex items-baseline gap-2">
              <span className="text-lg font-bold text-brand-orange-500">
                {formatARS(product.discountedPriceCents!)}
              </span>
              <span className="text-sm text-neutral-400 line-through">
                {formatARS(product.priceCents)}
              </span>
            </div>
          ) : (
            <span className="text-lg font-bold text-neutral-900">
              {formatARS(product.priceCents)}
            </span>
          )}
        </div>
      </div>
    </Link>
  );
}
