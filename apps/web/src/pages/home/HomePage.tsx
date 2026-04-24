import { Link } from 'react-router-dom';
import { useTranslation } from 'react-i18next';

import { ProductCard } from '@/components/catalog/ProductCard';
import { usePublicProducts } from '@/features/catalog/hooks';

export function HomePage() {
  const { t } = useTranslation();
  const { data: listing, isLoading } = usePublicProducts({
    sort: 'newest',
    limit: 8,
  });
  const featured = listing?.data ?? [];

  return (
    <>
      <section className="mx-auto max-w-4xl px-4 py-20 text-center md:px-6">
        <h1 className="font-display text-5xl font-bold text-brand-graphite-900 md:text-6xl">
          {t('home.headline')}{' '}
          <span className="text-brand-orange-500">{t('home.headlineAccent')}</span>
        </h1>
        <p className="mt-6 text-lg text-neutral-600">{t('home.subtitle')}</p>
        <div className="mt-10 flex flex-wrap justify-center gap-3">
          <Link
            to="/catalogo"
            className="inline-flex items-center rounded-md bg-brand-orange-500 px-6 py-3 font-medium text-white shadow-sm transition-colors hover:bg-brand-orange-600 focus-visible:shadow-focus"
          >
            {t('home.ctaCatalog')}
          </Link>
          <Link
            to="/catalogo"
            className="inline-flex items-center rounded-md border border-neutral-200 bg-neutral-0 px-6 py-3 font-medium text-brand-graphite-900 transition-colors hover:bg-neutral-50 focus-visible:shadow-focus"
          >
            {t('home.ctaCustomize')}
          </Link>
        </div>
      </section>

      {featured.length > 0 && (
        <section className="mx-auto max-w-7xl px-4 pb-20 md:px-6">
          <div className="mb-6 flex items-end justify-between">
            <h2 className="font-display text-2xl font-bold text-brand-graphite-900 md:text-3xl">
              Lo más nuevo
            </h2>
            <Link
              to="/catalogo"
              className="text-sm font-medium text-brand-orange-500 hover:text-brand-orange-600"
            >
              Ver todo →
            </Link>
          </div>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
            {featured.map((p) => (
              <ProductCard key={p.id} product={p} />
            ))}
          </div>
        </section>
      )}

      {!isLoading && featured.length === 0 && (
        <p className="mx-auto max-w-4xl px-4 pb-20 text-center font-mono text-xs text-neutral-400 md:px-6">
          {t('home.comingSoon')}
        </p>
      )}
    </>
  );
}
