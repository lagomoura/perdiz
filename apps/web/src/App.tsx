export default function App() {
  return (
    <main className="min-h-dvh bg-neutral-0">
      <header className="flex items-center justify-between border-b border-neutral-100 px-6 py-4">
        <div className="flex items-center gap-3">
          <img src="/brand/logo.svg" alt="p3rDiz" className="h-10 w-auto" />
        </div>
        <nav className="hidden gap-6 md:flex">
          <a className="text-sm font-medium text-neutral-600 hover:text-brand-graphite-900">
            Catálogo
          </a>
          <a className="text-sm font-medium text-neutral-600 hover:text-brand-graphite-900">
            Cómo funciona
          </a>
          <a className="text-sm font-medium text-neutral-600 hover:text-brand-graphite-900">
            Contacto
          </a>
        </nav>
      </header>

      <section className="mx-auto max-w-4xl px-6 py-24 text-center">
        <h1 className="font-display text-5xl font-bold text-brand-graphite-900 md:text-6xl">
          Imaginá. <span className="text-brand-orange-500">Imprimimos.</span>
        </h1>
        <p className="mt-6 text-lg text-neutral-600">
          Soluciones 3D con precisión técnica y alma argentina. Catálogo en camino.
        </p>
        <div className="mt-10 flex justify-center gap-3">
          <button className="rounded-md bg-brand-orange-500 px-6 py-3 font-medium text-white shadow-sm transition hover:bg-brand-orange-600">
            Ver catálogo
          </button>
          <button className="rounded-md border border-neutral-200 bg-neutral-0 px-6 py-3 font-medium text-brand-graphite-900 transition hover:bg-neutral-50">
            Personalizar
          </button>
        </div>
        <p className="mt-16 font-mono text-xs text-neutral-400">
          Scaffold v0 — ver docs/ para el plan completo.
        </p>
      </section>
    </main>
  );
}
