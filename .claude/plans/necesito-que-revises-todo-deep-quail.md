# Rediseño bold del frontend de CritiComida

## Context

CritiComida ya tiene aplicado parcialmente el brand v2 ("Especiería": Azafrán/Páprika/Albahaca + Cormorant Garamond + DM Sans, fondo Crema), pero el audit revela tres tipos de problemas:

1. **Deuda técnica de tokens** — `app/globals.css` (1969 líneas) mezcla aliases legacy (`--mainPink`, `--mainBlack`) con los semánticos nuevos, tiene hex hardcodeados sueltos (`#c62828`, etc.) y aparenta estar truncado al final.
2. **Violaciones de Krug ("Don't Make Me Think")** — botón "Crear" ambiguo (¿crear qué?), theme toggle sin label (mystery meat), active state de tabs/nav demasiado sutil, modal de auth sin URL profunda, sin sistema de toasts para feedback de acciones.
3. **Oportunidades editoriales sin tomar** — el hero del restaurante, el feed, las cards firma y el dish profile están "correctos" pero genéricos: no usan asimetría, no aprovechan Cormorant en titulares, no tienen textura ni motion firma. La directiva del usuario es **rediseño bold**, no solo pulido.

Outcome buscado: una capa de fundamentos limpia + 3 surfaces flagship rediseñadas con carácter editorial + sistema de UX-feedback completo, dejando admin/settings para una segunda pasada.

**Decisión:** `brand-identity-v2.md` es canónico. `brand-identity.md` v1 (rosa) queda solo como referencia histórica.

---

## Plan en fases (P0 → P2)

### FASE 0 — Foundations cleanup (P0, prerequisito de todo lo demás)

**Objetivo:** Una sola fuente de verdad de tokens + primitivas reusables que las fases siguientes consumen.

- **`app/globals.css`** — auditar y reescribir:
  - Eliminar aliases legacy (`--mainPink`, `--mainBlack`, `--mainGrey`) y migrar todos los consumos a tokens semánticos (`--action-primary`, `--text-primary`, etc.).
  - Reemplazar hex sueltos (`#c62828`, gradient rgba inline en líneas ~284, ~576) por `var(--color-paprika)` etc.
  - Verificar que el archivo no esté truncado (línea ~1968) y completar tokens de dark mode si faltan.
  - Definir 5 niveles de sombra warm-tinted (`--shadow-micro/base/media/elevated/floating`) según brand v2 §Shadows.
  - Definir easings firma (`--ease-spoon`, `--ease-standard`).
- **Crear primitivas faltantes en `app/components/ui/`** (existen Button/Badge/Avatar/Tabs/Input/Select/Chip/Skeleton/EmptyState/IconButton):
  - `Modal.tsx` — dialog accesible (focus trap, ESC, overlay), reemplaza usos ad-hoc en `AuthModal.tsx` y `ReportModal.tsx`.
  - `Toast.tsx` + `ToastProvider` — sistema global vía context, usar en compose/like/follow/save (resuelve Krug: "feedback inmediato").
  - `Tooltip.tsx` — labelled, con delay (reemplaza `.review-description-tooltip` ad-hoc en globals.css ~1084).
  - `Card.tsx` — encapsular `.cc-card`, variantes `flat | elevated | editorial`.
  - `RatingPill.tsx` — pill con número Cormorant + color dinámico (Albahaca ≥9, Azafrán 7-8.9, Carbón <7).
- **`app/components/ui/index.ts`** — exportar todo desde un solo barrel.
- **Documentar tokens** — agregar comentario en cabecera de globals.css apuntando a `docs/brand-identity-v2.md` como fuente de verdad.

**Verificación:** grep `#[0-9a-fA-F]{3,6}` en `app/**/*.{ts,tsx,css}` debe arrojar solo hex en `globals.css` (nunca en componentes); grep `mainPink|mainBlack|mainGrey` en `app/` debe ser 0.

---

### FASE 1 — Navigation & wayfinding (P0, Krug)

**Objetivo:** que un usuario nuevo nunca tenga que pensar dónde está, qué puede hacer ni a dónde lo lleva un click.

- **`app/components/nav/TopNav.tsx`** (líneas ~52-130):
  - Active state visible: subrayado Azafrán de 2px (no solo `bg-surface-subtle`). Usar el patrón ya correcto de `ui/Tabs.tsx`.
  - Renombrar "Crear" → "Publicar" + ícono `faPenToSquare` (el `faPlus` actual sugiere "agregar contacto"). Para anónimos, abrir AuthModal con `mode="register"` y mensaje "Iniciá sesión para publicar tu reseña".
  - `ThemeToggle.tsx` — agregar `aria-label` y `title` ("Cambiar a modo oscuro/claro").
  - "Iniciar sesión" también disponible en mobile (no solo desktop) — actualmente queda escondido detrás del avatar en `BottomNav.tsx`.
- **`app/components/nav/BottomNav.tsx`**:
  - Mismo cambio de label "Crear" → "Publicar".
  - Active state con punto Azafrán bajo el ícono (más legible en mobile que cambio de bg).
  - Mostrar siempre los 5 ítems con label de texto pequeño (DM Sans 0.6875rem) — los íconos solos son mystery meat.
- **`app/components/nav/AuthModal.tsx`** — dejar el modal pero **además** crear rutas reales `/login` y `/registro` que renderizan el mismo flow full-page. Permite deep-links y mejora SEO. El modal queda como "fast path" desde cualquier página.
- **Breadcrumbs editoriales en pages internas** (restaurant, dish, categoría): tipografía Cormorant pequeña sobre el hero, separador "·" en lugar de "/", color Carbón suave. No es navegación primaria pero ancla al usuario.

**Verificación:** Recorrer en browser (Playwright MCP) home → restaurant → dish → categoría sin tocar el botón Atrás; siempre debe verse a un golpe de vista (a) dónde estás y (b) cómo volver. Todos los íconos sin texto deben tener `aria-label`.

---

### FASE 2 — Feedback & estado del sistema (P0, Krug)

**Objetivo:** ninguna acción del usuario queda sin respuesta visible (ley de visibilidad del estado del sistema).

- Conectar el `ToastProvider` (creado en Fase 0) en `app/layout.tsx` y emitir desde:
  - `app/compose/ComposeClient.tsx` — al publicar reseña ("Reseña publicada · Ver").
  - Likes/follows/saves en `FeedList.tsx`, `RestaurantCard.tsx`, perfiles.
  - Errores de auth/API que hoy mueren silenciosamente.
- **Skeletons reales en lugar de spinners genéricos** — extender `Skeleton.tsx` con presets `<RestaurantCardSkeleton/>`, `<DishCardSkeleton/>`, `<FeedItemSkeleton/>` que matchen el shape exacto del componente final (Krug: reducir layout shift).
- **EmptyStates con voz de marca** — revisar todos los `EmptyState.tsx` y aplicar copy del brand v2 §Voice ("Todavía no hay reseñas." en lugar de "¡Sé el primero! 🎉").
- **Estados de loading/error/empty para `FeedList`, `SearchClient`, `TrendingClient`, `SavedClient`, `NotificationsClient`** — los 4 últimos comparten patrón: lista vacía + filtro sin resultados + error de red. Centralizar en un `<ListState>` wrapper.
- **Botones con loading state real** — `Button.tsx` ya tiene spinner; auditar que se use en cada submit (compose, login, follow). Si `loading=true`, el label debe cambiar ("Publicando..." en lugar de "Publicar") y el botón quedar deshabilitado.

**Verificación:** spawn manual de errores (kill backend en `:8002`) → cada acción muestra toast de error legible, nunca silencio. Network throttling 3G → cada lista muestra skeleton adecuado, no fondo en blanco.

---

### FASE 3 — Rediseño editorial de flagships (P1, frontend-design bold)

**Objetivo:** que la home, el restaurant profile, el dish profile y el feed sean memorables — no "otra app de comida". Aquí es donde el redesign **bold** se manifiesta. Cada surface elige una composición firma.

#### 3.1 Home / Landing (`app/page.tsx` + `app/components/EditorialLanding.tsx` + `FeedClient`)

- **Hero asimétrico**: titular Cormorant 500 italic clamp(3rem, 8vw, 6rem) en columna izq (60%), "manchón" de saffron `radial-gradient` desfasado en columna derecha (40%) con foto de plato en `aspect-ratio: 4/5` rotada -2deg. Subhead DM Sans pequeño.
- **Grain overlay** sutil (`background-image: url(noise.svg); opacity: 0.04`) sobre el fondo Crema — da textura "papel".
- **Sección "Plato de la semana"** intercalada en el feed cada N items: card a doble ancho con tratamiento editorial (Cormorant, kicker `LO IMPRESCINDIBLE` en uppercase tracking-wide Páprika).
- **Tabs `for_you` / `following`** — usar el patrón `ui/Tabs.tsx` (ya tiene underline correcto), no la variante custom.

#### 3.2 Restaurant profile v2 (`app/restaurants/[id]/`)

- **Hero rediseñado**: foto de portada full-bleed `aspect-[16/7]` con overlay `linear-gradient(180deg, transparent 40%, var(--color-carbon)/85% 100%)`. Nombre Cormorant 500 clamp(2.5rem, 6vw, 4.5rem) + ubicación en pill Azafrán pálido superpuesta cruzando el borde inferior del hero (pattern de magazine).
- **`RatingsRadar`** — mover a layout "tarjeta editorial" con número grande Cormorant 4rem a la izq y radar a la der; subrayado Azafrán bajo el número.
- **`RestaurantTabs.tsx`** (líneas ~98-112): cambiar a underline + active Azafrán, count badges con contraste real (Albahaca bg + Crema text para active, Crema-dark bg + Carbón-soft text para inactive).
- **"Platos firma"** — grid asimétrico (1 grande + 2 chicos por fila) en lugar de grid uniforme; primer plato siempre destacado con kicker `EL DE LA CASA`.
- **"Cerca"** — incluir hint visual de scroll horizontal (gradient fade en bordes) y usar `RestaurantCard` v2 con sombra elevated en hover.

#### 3.3 Dish profile v2 (`app/dishes/[id]/`)

- **Hero rotado**: foto de plato en cuadrado `aspect-square` con rotación -3deg y sombra warm `--shadow-elevated`, texto a la izq con nombre del plato Cormorant italic 500 clamp(2rem, 5vw, 4rem).
- **`RatingPill`** (creado en Fase 0) reemplaza el número plano actual.
- **"Taste profile"** — barras horizontales con animación `width 0 → final` al entrar en viewport (`prefers-reduced-motion` respeta).
- **Editorial Claude** — caja con borde-izq Azafrán 3px, fondo Crema-oscuro, atribución sutil ("Análisis editorial · CritiComida AI").
- **Related dishes** — carrusel horizontal con scroll-snap; primera y última card con shadow al borde para indicar overflow.

#### 3.4 Feed (`FeedList.tsx`, 187 líneas)

- **Card de reseña tipo carta postal**: avatar + handle arriba, foto de plato como protagonista (1:1), texto de reseña abajo en DM Sans con primera línea drop-cap Cormorant italic.
- **Botón de like con bounce ease** (`--ease-spoon`) y count que sube con tween, no salto.
- **Separador entre items**: línea 1px Crema-más-oscuro con un punto Azafrán al centro (no border-bottom plano).
- **Pull-to-refresh** indicator en mobile.

---

### FASE 4 — Surfaces secundarias y polish (P2)

- **`app/profile/`** y **`app/u/[userId]/`** — perfil de usuario con header tipo masthead editorial (avatar grande + nombre Cormorant + bio + counts en pills).
- **`app/compose/ComposeClient.tsx`** — flujo paso a paso con stepper, preview en vivo de la card que se publicará. Drag&drop de fotos con aspect-ratio sugerido 1:1.
- **`app/search/SearchClient.tsx`** — input full-width tipo "command bar" con resultados live, Cormorant 1.25rem para nombres de restaurante en sugerencias.
- **`app/categorias/[slug]/`** — heading editorial grande + descripción + grid bold.
- **`app/notifications/NotificationsClient.tsx`** — lista densa con tipo de evento como kicker uppercase Azafrán pequeño.
- **`app/saved/SavedClient.tsx`**, **`app/trending/TrendingClient.tsx`**, **`app/reviews/[id]/`** — aplicar tokens nuevos y cards v2.
- **`app/components/ChatWidget.tsx`** (165 líneas) — auditar contra brand v2; el chat asistente debe sentirse parte del mismo universo, no Intercom genérico.
- **`app/components/Footer.tsx`** — verificar que respeta brand v2 §Footer (Carbón bg, border-top 3px Azafrán claro, radius 2rem en top corners).
- **`app/about/`** — página About como pieza editorial (manifiesto), tipografía protagonista.
- **Admin (`app/admin/`)** — fuera de scope estético principal pero al menos consumir tokens nuevos para no romper en dark mode.

---

## Archivos críticos a modificar (mapa rápido)

| Surface | Archivo principal |
|---|---|
| Tokens | `app/globals.css` |
| Layout | `app/layout.tsx` (montar ToastProvider) |
| Primitivas | `app/components/ui/{Modal,Toast,Tooltip,Card,RatingPill}.tsx` (nuevos) |
| Nav | `app/components/nav/{TopNav,BottomNav,ThemeToggle,AuthModal}.tsx` |
| Auth | `app/login/page.tsx`, `app/registro/page.tsx` (nuevos) |
| Home | `app/page.tsx`, `app/components/EditorialLanding.tsx`, `app/components/feed/FeedClient.tsx` |
| Feed | `app/components/feed/FeedList.tsx` |
| Restaurant | `app/restaurants/[id]/page.tsx` + `components/RestaurantPageClient.tsx`, `RestaurantTabs.tsx` |
| Dish | `app/dishes/[id]/` (page + DishPageClient + DishTabs) |
| Cards | `app/components/RestaurantCard.tsx` |
| Profiles | `app/profile/`, `app/u/[userId]/` |
| Compose | `app/compose/ComposeClient.tsx` |

---

## Reutilizar lo que ya existe (no reinventar)

- `ui/Tabs.tsx` ya tiene underline + keyboard nav correcto → patrón a propagar a Nav y RestaurantTabs.
- `ui/Button.tsx` ya soporta loading + variants → usarlo siempre que haya un `<button>`.
- `ui/Skeleton.tsx` → extender con presets, no recrear.
- `useAuth()` hook + `AuthContext` → no duplicar lógica de token refresh.
- `fetchApi` en `app/lib/api/client.ts` → todo data fetching pasa por ahí.

---

## Verificación end-to-end

1. **Tokens**: `grep -rE "#[0-9a-fA-F]{3,6}|mainPink|mainBlack|mainGrey" app/ --include="*.{ts,tsx}"` → 0 resultados fuera de `globals.css`.
2. **Build**: `npm run build` debe pasar sin warnings nuevos. `npm run lint` clean.
3. **Visual smoke test (Playwright MCP)**: navegar home → click feed item → restaurant → tab Platos → dish → tab Reseñas → back → categoría → search; capturar screenshot por surface (light + dark) y comparar contra `docs/brand-identity-v2.md`.
4. **Krug checklist por surface**:
   - ¿Sé en qué página estoy de un golpe? (active nav state, breadcrumb, H1 visible)
   - ¿Sé qué hace cada botón sin hover? (label de texto + ícono coherente)
   - ¿Recibo feedback inmediato al hacer click? (toast, loading state, optimistic UI)
   - ¿Los íconos sin texto tienen `aria-label`? (axe DevTools por surface)
5. **Responsive**: 360px / 768px / 1280px sin scroll horizontal, sin texto cortado, hit targets ≥44×44.
6. **Reduced motion**: `@media (prefers-reduced-motion: reduce)` desactiva transforms (verificar en DevTools).
7. **Dark mode**: cada surface se ve intencional (no inversión rota); ChromaTokens (Azafrán/Páprika/Albahaca) sin cambiar — solo neutrals invertidos.
8. **Backend integration**: `npm run test:backend` sigue verde; el rediseño no toca la API.

---

## Orden de ejecución sugerido

1. **Sesión 1**: Fase 0 completa (tokens + primitivas). Sin tocar surfaces — esto desbloquea todo lo demás.
2. **Sesión 2**: Fase 1 + Fase 2 (nav + feedback). UX P0 cerrada.
3. **Sesión 3**: Fase 3.1 + 3.2 (home + restaurant). Las dos surfaces más vistas.
4. **Sesión 4**: Fase 3.3 + 3.4 (dish + feed).
5. **Sesión 5**: Fase 4 (secundarias + polish + verificación final).

Cada sesión termina con commit + screenshot review antes de seguir.
