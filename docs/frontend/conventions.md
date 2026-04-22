# Frontend — convenciones

Vinculante para todo código en `apps/web`.

## Stack y versiones

- TypeScript 5.x (strict)
- React 18
- Vite 5
- TailwindCSS 3 + `@tailwindcss/typography` + `@tailwindcss/forms`
- shadcn/ui (componentes de Radix + estilos Tailwind)
- react-hook-form + zod
- TanStack Query 5
- Zustand 4
- React Router 6
- three.js + @react-three/fiber + @react-three/drei
- Vitest + Testing Library + Playwright
- ESLint + Prettier

## Estructura de directorios

Estructura **feature-first**. Archivos compartidos en `components/`, `hooks/`, `lib/`.

```
apps/web/
├── index.html
├── vite.config.ts
├── tsconfig.json
├── tailwind.config.ts
├── postcss.config.js
├── package.json
├── public/
│   └── favicon.svg
└── src/
    ├── main.tsx
    ├── App.tsx
    ├── router.tsx
    ├── styles/
    │   ├── globals.css          # Tailwind directives + base styles
    │   └── tokens.css           # CSS variables (design tokens)
    ├── app/
    │   ├── providers.tsx        # QueryClient, Router, Theme, I18n
    │   └── layouts/
    │       ├── PublicLayout.tsx
    │       ├── AccountLayout.tsx
    │       └── AdminLayout.tsx
    ├── pages/                   # route-level containers (delgados; delegan a features)
    │   ├── home/
    │   ├── catalog/
    │   ├── product/
    │   ├── cart/
    │   ├── checkout/
    │   ├── account/
    │   ├── auth/
    │   └── admin/
    ├── features/                # lógica y UI agrupada por dominio
    │   ├── auth/
    │   ├── catalog/
    │   ├── cart/
    │   ├── customization/
    │   │   └── registry.ts      # TYPE → componente render
    │   ├── three-preview/
    │   ├── orders/
    │   ├── admin-products/
    │   └── ...
    ├── components/              # componentes reutilizables sin dominio
    │   ├── ui/                  # shadcn generados (Button, Dialog, Input, ...)
    │   ├── layout/              # Header, Footer, Sidebar, Nav
    │   ├── feedback/            # Toast wrappers, EmptyState, ErrorBoundary
    │   └── data/                # DataTable, Pagination, Filters
    ├── hooks/                   # hooks de uso transversal
    ├── stores/                  # Zustand stores (cart-ui, auth, theme)
    ├── services/
    │   ├── api/                 # cliente generado + wrappers
    │   │   ├── client.ts        # fetch con auth, refresh automático, manejo errores
    │   │   └── generated/       # autogenerado desde OpenAPI (no tocar a mano)
    │   ├── auth.ts
    │   └── analytics.ts
    ├── lib/
    │   ├── format.ts            # formateadores ARS, fechas, pluralización
    │   ├── i18n.ts
    │   └── utils.ts
    ├── types/                   # tipos globales
    └── test/
        ├── setup.ts
        └── fixtures/
```

## Reglas de imports

- Alias configurados: `@/` apunta a `src/`.
- Orden: librerías externas → módulos `@/lib|hooks|services` → `@/components|features` → archivos relativos. Automático con ESLint `import/order`.
- **Prohibido** importar entre features hermanas (`features/cart` no importa de `features/catalog`). Si algo se comparte, promoverlo a `components/` o `lib/`.
- **Prohibido** imports relativos que suban más de 1 nivel (`../../../`); usar alias.

## Routing

- React Router 6 con data routers y lazy loading por ruta.
- Estructura:

```
/                               (home)
/catalogo                       (listado general)
/catalogo/:categorySlug         (por categoría)
/producto/:slug                 (detalle)
/carrito
/checkout                       (autenticado + verificado)
/checkout/exito/:orderId
/mi-cuenta                      (autenticado)
/mi-cuenta/pedidos
/mi-cuenta/pedidos/:id
/mi-cuenta/direcciones
/mi-cuenta/seguridad
/mi-cuenta/wishlist
/auth/ingresar
/auth/registrarse
/auth/olvide-password
/auth/resetear-password
/auth/verificar-email
/auth/oauth/callback/:provider
/admin                          (admin only; 404 si no)
/admin/productos
/admin/productos/:id
/admin/categorias
/admin/pedidos
/admin/pedidos/:id
/admin/usuarios
/admin/cupones
/admin/auditoria
/admin/configuracion
```

- **Guards**: loader en cada ruta protegida consulta `authStore`; si no autorizado, redirect o throw 404.
- **Code-splitting**: cada página hoja es `lazy()`.

## Manejo de estado

- **Servidor** (datos que vienen del API): **TanStack Query**. Nunca duplicar en Zustand.
  - Keys estructuradas: `['products', { filters }]`, `['product', slug]`, `['cart']`, etc.
  - `staleTime` por tipo: 30s catálogo, 0s carrito/pedidos.
  - Invalidaciones explícitas tras mutaciones.
- **Cliente**: **Zustand**, un store por dominio pequeño (auth, cart-ui overlay, theme). No un megastore.
- **URL** como estado: filtros de catálogo, paginación, tabs. Usar `useSearchParams`. La URL es la fuente de verdad para lo que se comparte.
- **No** guardar access token en Zustand persistido; en memoria simple (`authStore` sin `persist`).

## API client

- Generado desde OpenAPI en CI: `npm run api:gen` produce `src/services/api/generated/`.
- Wrapper en `src/services/api/client.ts`:
  - Inyecta `Authorization` con access token.
  - Intercepta 401: intenta `POST /auth/refresh` una vez; si falla, limpia auth y redirige a `/auth/ingresar`.
  - Añade `Idempotency-Key` (ULID nuevo) en POSTs de mutación sensibles (checkout, agregar al carrito).
  - Mapea errores del backend (`error.code`) a clase `ApiError` con traducción al español.
- **Prohibido** usar `fetch` directo en features. Todo pasa por el wrapper.

## Formularios

- `react-hook-form` + `zod` (resolver `@hookform/resolvers/zod`).
- Schemas zod viven junto al formulario: `features/auth/schemas.ts`.
- Validación server-side siempre prevalece; si falla, mapear el `error.details.field` al campo y mostrar.
- Inputs con `aria-invalid`, mensaje asociado por `aria-describedby`.

## Internationalización

- `react-i18next` configurado aunque solo haya locale `es-AR`.
- Todos los strings visibles van por `t('...')` desde el inicio. Keys planas en dot-notation (`checkout.payment.submit`).
- **No hardcodear** strings en componentes. Revisión CI con `eslint-plugin-i18next` (o similar) para detectar strings sueltos.

## Accesibilidad

- Cumplimiento **WCAG 2.1 AA**.
- Foco visible siempre: shadow `shadow.focus` (definido en tokens).
- Navegación completa por teclado probada manualmente y con Playwright en flujos críticos (login, carrito, checkout).
- Aria roles correctos en componentes custom. shadcn/ui ya cumple en su mayoría.
- Respeto a `prefers-reduced-motion` y `prefers-color-scheme`.
- Contraste AA mínimo. Nunca color como único canal de info (iconos + texto, swatch + aria-label).
- Skip link al main en cada layout.

## Estilos

- **Tailwind como único sistema de estilos**. Sin CSS Modules, sin styled-components.
- Tokens en `src/styles/tokens.css` como CSS vars; Tailwind config referencia las vars (`colors: { brand: { orange: 'rgb(var(--brand-orange) / <alpha-value>)' } }`).
- Clases extensas se **extraen** a un componente, no a `@apply` (excepto en `ui/`).
- `cn(...)` helper (clsx + tailwind-merge) para componer clases condicionales.

## Preview 3D

- Componente `features/three-preview/ModelViewer.tsx`:
  - Props: `url` (GLB), `background?`, `autoRotate?`, `className?`.
  - Usa `@react-three/fiber` + `Suspense` con fallback skeleton.
  - Luces: `ambient` baja + `directional` principal + `point` de relleno.
  - Cámara: `PerspectiveCamera` + `OrbitControls` (drag/zoom).
  - Respeta `prefers-reduced-motion` desactivando `autoRotate`.
  - Timeout de carga: 10s → fallback a imagen estática con mensaje.
  - Nunca descargar GLB > 20MB (el preview debe estar optimizado por Draco).

## Error handling

- `ErrorBoundary` global en `AppProviders` que captura errores de render y muestra pantalla de fallback con botón de recarga; reporta a Sentry.
- Errores de queries/mutaciones: manejados explícitamente por cada componente con `isError`, `error`. Nunca toasts silenciosos a ciegas.
- Traducción de `error.code` → mensaje en `src/lib/errors.ts` como mapa.

## Testing

- **Vitest** para unit + component.
- **Testing Library** para componentes (sin testear implementación, testear comportamiento observable).
- **Playwright** para E2E: smoke tests de home, login, agregar al carrito, checkout mock, admin login.
- Tests co-locados: `Component.tsx` + `Component.test.tsx`.
- Cobertura no es target rígido; la regla es: **toda feature con lógica no trivial tiene tests** antes de mergear.

## Performance

- Lighthouse objetivo: **Performance 90+**, **Accessibility 95+** en home y catálogo en mobile 4G simulado.
- Imágenes: `<img loading="lazy">` excepto hero; WebP con fallback JPEG; dimensiones fijas para evitar CLS.
- Bundle: code-split por ruta + lazy del viewer 3D (pesado, no debe estar en main bundle).
- Fonts: self-hosted vía `@fontsource/inter` y `@fontsource/space-grotesk` para evitar FOUT.
- Prefetch de rutas probables con `<link rel="prefetch">` al hover (React Router lo soporta nativamente).

## SEO

- SPA con `react-helmet-async` para títulos y metas por ruta.
- Ficha de producto: OG tags, Twitter card, JSON-LD `Product` con precio y disponibilidad.
- sitemap.xml y robots.txt servidos desde `public/`.
- **Nota**: SPA-only en MVP. Si SEO de catálogo se vuelve crítico, considerar migrar a SSR (Next.js o Vite SSR) en v2.

## Commits y PRs

- Mismas reglas que backend (Conventional Commits).
- PRs de UI incluyen screenshots o gif cuando cambian vistas significativas.

## Herramientas de CI

- `npm run typecheck` — tsc --noEmit.
- `npm run lint` — eslint.
- `npm run format:check` — prettier.
- `npm run test` — vitest run.
- `npm run test:e2e` — playwright.
- `npm run build` — Vite production build.
- CI falla si cualquier paso falla o si bundle main excede 250KB gzip (ajustable).
