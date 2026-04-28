import { Link } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import {
  ArrowRight,
  Layers,
  Palette,
  Ruler,
  Sparkles,
  Truck,
  Zap,
} from 'lucide-react';

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
      <section className="relative overflow-hidden">
        <div aria-hidden className="pointer-events-none absolute inset-0">
          <div className="absolute -top-40 right-0 h-[600px] w-[600px] rounded-full bg-gradient-to-br from-brand-orange-500/20 via-brand-amber-500/10 to-transparent blur-3xl" />
          <div className="absolute -left-32 bottom-[-200px] h-[500px] w-[500px] rounded-full bg-gradient-to-tr from-brand-orange-600/15 to-transparent blur-3xl" />
        </div>

        <div className="relative mx-auto grid max-w-7xl items-center gap-10 px-4 py-20 md:grid-cols-2 md:px-6 md:py-28">
          <div>
            <span className="inline-flex items-center gap-2 rounded-full border border-brand-orange-500/40 bg-brand-orange-500/10 px-3 py-1 text-xs font-medium text-brand-orange-500">
              <Sparkles size={14} /> Impresión 3D en Argentina
            </span>
            <h1 className="mt-5 font-display text-5xl font-bold leading-tight text-neutral-900 md:text-7xl">
              {t('home.headline')}{' '}
              <span className="bg-gradient-to-r from-brand-orange-500 to-brand-amber-500 bg-clip-text text-transparent">
                {t('home.headlineAccent')}
              </span>
            </h1>
            <p className="mt-6 max-w-xl text-lg text-neutral-600">
              {t('home.subtitle')}
            </p>
            <div className="mt-10 flex flex-wrap gap-3">
              <Link
                to="/catalogo"
                className="inline-flex items-center gap-2 rounded-md bg-brand-orange-500 px-6 py-3 font-medium text-white shadow-md transition-colors hover:bg-brand-orange-600 focus-visible:shadow-focus"
              >
                {t('home.ctaCatalog')}
                <ArrowRight size={18} />
              </Link>
              <Link
                to="/catalogo"
                className="inline-flex items-center rounded-md border border-neutral-200 bg-neutral-50 px-6 py-3 font-medium text-neutral-900 transition-colors hover:bg-neutral-100 focus-visible:shadow-focus"
              >
                {t('home.ctaCustomize')}
              </Link>
            </div>
          </div>

          <div className="relative hidden md:block">
            <div className="relative mx-auto aspect-square max-w-md">
              <div className="absolute inset-8 rounded-full bg-gradient-to-br from-brand-orange-500/30 via-brand-amber-500/20 to-transparent blur-2xl" />
              <div className="absolute inset-0 rounded-full border border-brand-orange-500/30" />
              <div className="absolute inset-8 rounded-full border border-brand-orange-500/20" />
              <div className="absolute inset-16 rounded-full border border-brand-orange-500/10" />
              <div className="absolute inset-0 flex items-center justify-center">
                <div className="w-3/4 space-y-2">
                  {[55, 70, 90, 100, 90, 70, 55].map((w, i) => (
                    <div
                      key={i}
                      className="h-3 rounded-sm bg-gradient-to-r from-brand-orange-500 to-brand-amber-500"
                      style={{
                        width: `${w}%`,
                        marginLeft: `${(100 - w) / 2}%`,
                        opacity: 0.4 + (i / 12),
                      }}
                    />
                  ))}
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      <section className="border-y border-neutral-100 bg-neutral-50/40">
        <div className="mx-auto grid max-w-7xl gap-6 px-4 py-10 sm:grid-cols-2 md:grid-cols-4 md:px-6">
          {[
            { icon: Layers, title: 'PLA, PETG, ABS, Resina', label: 'Materiales' },
            { icon: Ruler, title: '±0.1 mm', label: 'Tolerancia' },
            { icon: Palette, title: 'Color y acabado', label: 'Personalización' },
            { icon: Truck, title: '3 a 7 días', label: 'Plazos' },
          ].map(({ icon: Icon, title, label }) => (
            <div key={label} className="flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-brand-orange-500/10 text-brand-orange-500">
                <Icon size={20} />
              </div>
              <div>
                <p className="text-xs uppercase tracking-wider text-neutral-400">
                  {label}
                </p>
                <p className="font-medium text-neutral-900">{title}</p>
              </div>
            </div>
          ))}
        </div>
      </section>

      <section id="como-funciona" className="mx-auto max-w-7xl px-4 py-20 md:px-6">
        <div className="mb-12 text-center">
          <h2 className="font-display text-3xl font-bold text-neutral-900 md:text-4xl">
            Cómo funciona
          </h2>
          <p className="mt-3 text-neutral-600">De la idea al modelo, en capas.</p>
        </div>
        <div className="grid gap-6 md:grid-cols-3">
          {[
            {
              n: '01',
              icon: Sparkles,
              title: 'Elegí o subí tu modelo',
              desc: 'Pedí algo del catálogo o mandanos tu STL. Te ayudamos a definir material y acabado.',
            },
            {
              n: '02',
              icon: Zap,
              title: 'Lo imprimimos',
              desc: 'Producción con tolerancias técnicas y revisión pieza por pieza antes de despachar.',
            },
            {
              n: '03',
              icon: Truck,
              title: 'Lo recibís',
              desc: 'Envío a todo el país o retiro en CABA. Te avisamos cuando está listo.',
            },
          ].map(({ n, icon: Icon, title, desc }) => (
            <div
              key={n}
              className="relative rounded-xl border border-neutral-100 bg-neutral-50 p-6 transition-colors hover:border-brand-orange-500/40"
            >
              <span className="absolute right-6 top-6 font-mono text-xs text-neutral-400">
                {n}
              </span>
              <div className="mb-4 flex h-12 w-12 items-center justify-center rounded-lg bg-brand-orange-500/10 text-brand-orange-500">
                <Icon size={22} />
              </div>
              <h3 className="font-display text-lg font-bold text-neutral-900">
                {title}
              </h3>
              <p className="mt-2 text-sm text-neutral-600">{desc}</p>
            </div>
          ))}
        </div>
      </section>

      {featured.length > 0 && (
        <section className="mx-auto max-w-7xl px-4 pb-20 md:px-6">
          <div className="mb-6 flex items-end justify-between">
            <h2 className="font-display text-2xl font-bold text-neutral-900 md:text-3xl">
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

      <section className="mx-auto max-w-7xl px-4 pb-24 md:px-6">
        <div className="relative overflow-hidden rounded-2xl border border-brand-orange-500/30 bg-gradient-to-br from-neutral-50 to-neutral-100 p-10 text-center md:p-16">
          <div
            aria-hidden
            className="pointer-events-none absolute -right-20 -top-20 h-80 w-80 rounded-full bg-gradient-to-br from-brand-orange-500/20 to-brand-amber-500/10 blur-3xl"
          />
          <div className="relative">
            <h2 className="font-display text-3xl font-bold text-neutral-900 md:text-4xl">
              ¿Tenés un proyecto en mente?
            </h2>
            <p className="mx-auto mt-4 max-w-xl text-neutral-600">
              Mandanos tu STL o contanos qué necesitás. Cotizamos en menos de 24 hs.
            </p>
            <Link
              to="/catalogo"
              className="mt-8 inline-flex items-center gap-2 rounded-md bg-brand-orange-500 px-8 py-4 font-medium text-white shadow-md transition-colors hover:bg-brand-orange-600 focus-visible:shadow-focus"
            >
              {t('home.ctaCustomize')} <ArrowRight size={18} />
            </Link>
          </div>
        </div>
      </section>

      {!isLoading && featured.length === 0 && (
        <p className="mx-auto max-w-4xl px-4 pb-12 text-center font-mono text-xs text-neutral-400 md:px-6">
          {t('home.comingSoon')}
        </p>
      )}
    </>
  );
}
