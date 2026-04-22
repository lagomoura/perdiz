import { Link } from 'react-router-dom';
import { useTranslation } from 'react-i18next';

export function HomePage() {
  const { t } = useTranslation();

  return (
    <section className="mx-auto max-w-4xl px-4 py-24 text-center md:px-6">
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
      <p className="mt-16 font-mono text-xs text-neutral-400">{t('home.comingSoon')}</p>
    </section>
  );
}
