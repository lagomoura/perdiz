# Plan — Enriquecer /dishes/[id] (página estrella v2)

## Context

El plato es la **entidad primaria** de CritiComida (sin platos no hay reviews, sin reviews no hay feed). Hoy `/dishes/[id]` es delgada: hero + 3 stats + lista de PostCard. La página de restaurante ya se rediseñó como "página estrella" (tabs sticky, agregados, signature dishes, diary pulse, photo mosaic, nearby) y el plato debe tener al menos la misma densidad informativa — además, ser el lugar donde el usuario decide **qué pedir** en el local, no solo dónde ir. Este plan refleja decisiones del 2026-04-27: alcance "espejo completo de restaurants v2", todos los bloques de enriquecimiento, jerarquía editorial-first, y una sección nueva de **historia del plato** generada por IA/Google.

## Outcome

- `/dishes/[id]` se vuelve Server Component async con `Promise.allSettled` y tabs sticky (Resumen / Reseñas / Fotos / En el restaurante).
- Aparece un **Taste Profile** (tags + pros/cons agregados), distribuciones cuantitativas (rating histograma, porciones, would-order-again), **Photo Mosaic** UGC, **Diary Pulse** social, **contexto del restaurante** embebido, **Related Dishes** (mismo plato en otros locales) y **Editorial Story** (blurb generado por Claude o Google Search sobre el plato en este local).
- El backend gana endpoints simétricos a los de restaurant: `aggregates`, `photos`, `diary-stats`, `related`, y `editorial-blurb`.
- DishReview gana un campo `dimension_ratings` ligero (sabor / presentación / porción / relación calidad-precio) — opcional, pero se documenta como Fase 2.

## Ramas de trabajo

### Fase A — Backend: agregados + contexto

**1. Migración Alembic nueva** — `backend/alembic/versions/0XX_dish_editorial_enrichment.py`:
   - Añadir a tabla `dishes`:
     - `editorial_blurb TEXT NULL`
     - `editorial_blurb_lang VARCHAR(8) NULL`
     - `editorial_blurb_source VARCHAR(20) NULL` (`claude` | `google` | `manual`)
     - `editorial_cached_at TIMESTAMPTZ NULL`
   - Espejo del patrón ya aplicado a `restaurants` por `014_restaurant_google_enrichment.py`.

**2. Nuevo router `backend/app/routers/dishes_aggregates.py`** (o extender `dishes_social.py`):
   - `GET /api/social/dishes/{id}/aggregates` → `DishAggregatesResponse`:
     - `pros_top: list[{text, count}]` (de `DishReviewProsCons.type='pro'`)
     - `cons_top: list[{text, count}]` (idem `'con'`)
     - `tags_top: list[{tag, count}]` (de `DishReviewTag`)
     - `rating_histogram: { "1": n, "2": n, "3": n, "4": n, "5": n }`
     - `portion_distribution: { small: n, medium: n, large: n }`
     - `would_order_again: { yes: n, no: n, no_answer: n, pct: float|null }`
     - `photos_count: int`, `unique_eaters: int`
   - `GET /api/social/dishes/{id}/photos?cursor=&limit=24` → cursor-paginated `DishPhoto[]` (de `DishReviewImage` join review.created_at desc), incluye `dish.cover_image_url` como primer item lógico.
   - `GET /api/social/dishes/{id}/diary-stats` → `DishDiaryStats`:
     - `unique_eaters`, `reviews_total`, `reviews_last_7d`, `recent_eaters: list[{user_id, display_name, avatar_url}]` (top 8 por created_at desc).
   - `GET /api/social/dishes/{id}/related?limit=6` → `RelatedDishItem[]`:
     - Otros `dishes` con `name ILIKE '%<token>%'` en restaurantes ≠ self, ordenados por `review_count desc, computed_rating desc`. Tokenización simple del nombre (split por espacios, descartar stopwords ES de ≤3 chars). Pre-filtrar misma `restaurant.location_name` cuando exista.
     - Devolver: `id, name, restaurant_id, restaurant_name, restaurant_location, cover_image_url, computed_rating, review_count`.
   - `GET /api/social/dishes/{id}/editorial-blurb` → `{blurb, source, lang, cached_at}` o `204` si no hay.
   - `POST /api/social/dishes/{id}/refresh-editorial` (admin/critic) → fuerza regenerar.

**3. Servicio `backend/app/services/dish_service.py`** — funciones nuevas:
   - `compute_dish_aggregates(db, dish_id)` (una sola query con CTEs / múltiples subqueries en `Promise.allSettled` style, similar a `restaurant_service.compute_aggregates`).
   - `get_dish_photos(db, dish_id, cursor, limit)` — paginado por `uploaded_at`.
   - `get_dish_diary_stats(db, dish_id)` — joins a `users` para avatars; reutiliza patrón de `restaurant_service.get_diary_stats`.
   - `get_related_dishes(db, dish, limit)` — query ILIKE descrita arriba.

**4. Editorial Blurb generator** — `backend/app/services/dish_editorial_enricher.py` (nuevo):
   - Análogo a `google_places_enricher.py` pero para platos.
   - Estrategia: usar **Anthropic Claude API** (modelo `claude-haiku-4-5-20251001` por costo/latencia) con prompt:
     - input: `dish.name`, `restaurant.name`, `restaurant.location_name`, `restaurant.cuisine_types`, `dish.description`
     - output esperado: 2-3 frases en español sobre la historia/origen del plato y por qué tiene sentido en ese local. Tono editorial.
   - Caching: una sola generación por dish, persistida en `dishes.editorial_blurb`. TTL configurable; default sin expiración.
   - Trigger: lazy en `GET /api/social/dishes/{id}` con `BackgroundTasks` cuando `editorial_blurb IS NULL` y `ANTHROPIC_API_KEY` está configurada. Degrada silencioso si no hay clave (igual que Google Places enricher hoy).
   - Skill `claude-api` aplica → incluir prompt caching en system prompt para reutilizar instrucciones.
   - Variante secundaria (futuro): scrapear Google Search snippet — descartado en v1 por fragilidad.

**5. Enriquecer `GET /api/social/dishes/{id}`** (existente, `dishes_social.py:31`) para devolver además:
   - `description: str | None`
   - `editorial_blurb: str | None`
   - `restaurant_cover_url`, `restaurant_location_name`, `restaurant_average_rating`, `restaurant_lat`, `restaurant_lon` (para card y distancia)
   - `is_signature: bool` (si el dish está entre los top-N por review_count del restaurante; reutilizar `compute_signature_dishes`).
   - `created_by_display_name` (para crédito si fue añadido por crítico).

**6. Tests** — `backend/tests/`:
   - `test_dishes_aggregates.py`: cubre cada endpoint nuevo con fixture de dish con N reviews.
   - `test_dish_editorial.py`: blurb cache hit/miss, sin clave → 204.
   - `test_related_dishes.py`: ILIKE matching y filtro self.

### Fase B — Frontend: tipos y API client

**7. Tipos nuevos** — `app/lib/types/dish.ts`:
   - `DishDetail` (extendido — actualmente vive en `app/lib/types/social.ts:129`): añadir `description`, `editorialBlurb`, `editorialSource`, `restaurantCoverUrl`, `restaurantLocationName`, `restaurantAverageRating`, `restaurantLat`, `restaurantLon`, `isSignature`, `createdByDisplayName`.
   - `DishAggregates`, `DishPhoto`, `DishDiaryStats`, `RelatedDishItem`, `DishRatingHistogram`, `DishPortionDistribution`.

**8. API client** — `app/lib/api/dishes-social.ts` (extender):
   - `getDishAggregates(dishId)`
   - `getDishPhotos(dishId, { cursor, limit })`
   - `getDishDiaryStats(dishId)`
   - `getRelatedDishes(dishId, { limit })`
   - `getDishEditorialBlurb(dishId)` (opcional — si el blurb ya viene en `getDishDetail`, este endpoint sólo se usa en refresh manual).
   - Mocks correspondientes en `app/lib/api/_mocks/dishes-social.ts` para que `isSocialMockEnabled()` siga funcionando.

### Fase C — Frontend: refactor de la página

**9. Convertir `app/dishes/[id]/page.tsx` a Server Component async**:
   - Patrón idéntico a `app/restaurants/[id]/page.tsx:44` — `Promise.allSettled` paralelo de: `getDishDetail`, `getDishAggregates`, `getDishPhotos`, `getDishDiaryStats`, `getRelatedDishes`, `getDishReviews` (primera página).
   - `generateMetadata`: title `"<name> — <restaurant> · CritiComida"`, description = `editorialBlurb || dish.description || "Reseñas, fotos y opiniones del plato"`. OG image = `heroImage || restaurantCoverUrl`.
   - 404 vía `notFound()` cuando `getDishDetail` lanza `ApiError` 404. Crear `app/dishes/[id]/not-found.tsx` y `app/dishes/[id]/loading.tsx` (espejo de `app/restaurants/[id]/loading.tsx`).
   - Pasar todos los datos a un nuevo `DishPageClient` (ver siguiente).

**10. Estructura de componentes — `app/dishes/[id]/components/`** (nueva carpeta):

   - **`DishPageClient.tsx`** (Client) — root: maneja tab state (URL `?tab=`), pasa data a islas. Espejo de `RestaurantPageClient.tsx`.
   - **`DishHeroV2.tsx`** (Server) — hero full-bleed responsive (288/352/416px), gradient overlay, badges (categoría, price_tier, rating CritiComida + restaurant rating), Cormorant 4xl–6xl para nombre, breadcrumb "← <restaurant_name>" linkeado, autor crítico si existe.
   - **`DishTabs.tsx`** (Client) — sticky tablist (top-14, z-20), URL-synced, keyboard nav. Tabs: Resumen, Reseñas, Fotos, En el restaurante. Mismo patrón que `RestaurantTabs.tsx`.
   - **`DishActionsBar.tsx`** (Client) — barra sticky bajo hero: "Escribir reseña" (azafrán), Guardar, Compartir, "Ver en menú del local". Espejo de `RestaurantActionsBar.tsx`.
   - **`EditorialStoryCard.tsx`** (Server) — tarjeta crema con borde azafrán, Cormorant itálica, blurb editorial + atribución "Generado vía Claude" / "Vía Google Places". Espejo de `EditorialSummaryCard.tsx`. Si `editorialBlurb` es null, no renderiza.
   - **`DishDescriptionCard.tsx`** (Server) — `dish.description` con tipografía editorial. Si null, no renderiza.
   - **`TasteProfile.tsx`** (Server) — sección con dos columnas:
     - Izquierda: top tags (pills, max 12) tomados de `aggregates.tags_top`, ordenados por count.
     - Derecha: pros/cons agregados (reusa lógica visual de `ProsConsAggregated.tsx`, copia-paste y simplificar import).
   - **`DishStatsPanel.tsx`** (Server) — bloque de distribuciones:
     - Histograma horizontal de ratings 1★–5★ (barras con `--color-azafran`).
     - Donut o stacked bar de porción S/M/L (`--color-canela`/`--color-albahaca`/`--color-paprika`).
     - "Volverían a pedirlo": número grande + barra horizontal Sí/No.
     - "Plato firma" badge si `isSignature`.
   - **`DishPhotoMosaic.tsx`** (Client) — masonry de `DishReviewImage[]` + cover. Reusa `Lightbox.tsx` de `app/restaurants/[id]/components/Lightbox.tsx` (mover a `app/components/ui/Lightbox.tsx` para compartir limpio, o importar directo si no se duplica).
   - **`DishDiaryPulse.tsx`** (Server) — variante de `DiaryPulse.tsx`: stats (unique_eaters, reviews_total, last_7d) + recent_eaters avatars. Sin "most-ordered dish" porque ya estamos en uno.
   - **`RestaurantContextCard.tsx`** (Server) — card embebida del restaurante anfitrión: cover, nombre (link), location_name, rating CritiComida + Google, OpenStatus (reusa `app/restaurants/[id]/components/OpenStatus.tsx`), DistanceBadge si tenemos `useUserLocation` (Client wrapper). CTA "Ver el restaurante completo →".
   - **`RelatedDishesCarousel.tsx`** (Client) — horizontal scroll de otros restaurantes con el mismo plato. Cada card: cover del dish, nombre del restaurante, distancia (si lat/lon disponibles), rating, pill "$X". Header: "¿Dónde más probar <dish.name>?". Si `relatedDishes.length === 0`, oculto.
   - **`DishReviewsTab.tsx`** (Client) — extrae la lógica actual de listado + paginación; añade filtros simples (orden: relevancia / recientes / mejor / peor; toggle "solo con fotos"). Reusa `PostCard` y `usePostsInteraction`.

**11. Layout de la pestaña "Resumen" (orden editorial-first)**:
   1. `DishActionsBar` (sticky)
   2. `DishDescriptionCard` (si hay description)
   3. `EditorialStoryCard` (si hay blurb)
   4. `DishStatsPanel` (rating histogram + porciones + would-order-again)
   5. `TasteProfile` (tags + pros/cons)
   6. `DishDiaryPulse`
   7. `RestaurantContextCard`
   8. `RelatedDishesCarousel`
   9. Sneak peek 3 mejores reviews → CTA "Ver todas las reseñas →" (cambia a tab Reseñas)

**12. Mover el cliente actual** — `DishDetailClient.tsx` queda deprecated; su lógica de reviews migra a `DishReviewsTab.tsx`. No borrar inmediatamente, comentar como "remplazado por DishPageClient v2" para revisar en una segunda PR.

### Fase D — Verificación end-to-end

**13. Playwright (MCP)** — flujos manuales:
   - `mcp__playwright-mcp__browser_navigate` a `/dishes/<id-real>` con DB seedada.
   - Verificar: tabs sticky funcionan al hacer scroll, deep-link `?tab=fotos` abre la pestaña correcta.
   - Lightbox abre/cierra/navega.
   - "Escribir reseña" navega a `/compose?dish=<id>` cuando hay sesión.
   - Mobile snapshot 390x844.

**14. Tests automatizados**:
   - Backend: `npm run test:backend` debe pasar con los nuevos tests de Fase A·6.
   - Frontend: si hay vitest setup, snapshot de cada componente nuevo (no es bloqueante — el repo no tiene tests JS visibles hoy).

**15. Lint/build**: `npm run lint && npm run build`. Cero `'use client'` en archivos sin estado.

**16. Smoke test sin backend**: con `NEXT_PUBLIC_SOCIAL_MOCK=1` la página debe renderizar usando mocks (extender `mockGetDishDetail` para los campos nuevos y agregar mocks de aggregates/photos/diary/related).

**17. Verificar editorial blurb**: con `ANTHROPIC_API_KEY` configurada en backend `.env`, primer hit a `GET /api/social/dishes/{id}` debe disparar background task; segundo hit debe tener `editorial_blurb` poblado. Log de la generación visible en stdout del backend.

## Archivos críticos a modificar / crear

**Backend (modificar)**:
- `backend/alembic/versions/0XX_dish_editorial_enrichment.py` (nuevo)
- `backend/app/models/dish.py` (añadir columnas editorial)
- `backend/app/routers/dishes_social.py` (enriquecer GET detail; extender o split a `dishes_aggregates.py`)
- `backend/app/services/dish_service.py` (funciones de aggregates/photos/diary/related)
- `backend/app/services/dish_editorial_enricher.py` (nuevo)
- `backend/app/schemas/feed.py` o nuevo `schemas/dish_aggregates.py` (response models)
- `backend/app/main.py` (registrar router si se crea uno nuevo)

**Frontend (modificar/crear)**:
- `app/dishes/[id]/page.tsx` (refactor Server Component)
- `app/dishes/[id]/loading.tsx` (nuevo)
- `app/dishes/[id]/not-found.tsx` (nuevo)
- `app/dishes/[id]/components/*.tsx` (12 componentes nuevos listados arriba)
- `app/dishes/[id]/DishDetailClient.tsx` (deprecar, mover lógica)
- `app/lib/api/dishes-social.ts` (5 funciones nuevas + mocks)
- `app/lib/api/_mocks/dishes-social.ts` (mocks extendidos)
- `app/lib/types/social.ts` o `app/lib/types/dish.ts` (tipos nuevos)

## Reutilización / no duplicar

- **Lightbox** (`app/restaurants/[id]/components/Lightbox.tsx`) → mover a `app/components/ui/Lightbox.tsx` y reusar desde ambos.
- **OpenStatus**, **DistanceBadge** → reusar tal cual desde `app/restaurants/[id]/components/`. No duplicar; importar.
- **`useUserLocation` hook** (`app/lib/hooks/useUserLocation.ts`) → reusar para distancia en `RestaurantContextCard` y `RelatedDishesCarousel`.
- **`PostCard`** (`app/components/social/PostCard.tsx`) → reusar para listado de reseñas.
- **`usePostsInteraction`** → reusar para like/save.
- **`ProsConsAggregated.tsx`** lógica visual → idealmente extraer a `app/components/aggregates/ProsConsList.tsx` parametrizable, y consumir desde restaurants y dishes.
- **`compute_signature_dishes`** (backend) → reusar para flag `is_signature`.

## Dependencias / variables de entorno

- `ANTHROPIC_API_KEY` en backend `.env` (nuevo, opcional — sin él, editorial degrada silencioso).
- `anthropic` SDK Python instalado en backend (`pip install anthropic`, agregar a `requirements.txt`).
- Sin nuevas envs en frontend.

## No-objetivos (explícitos)

- No agregamos rating multidimensional al modelo `DishReview` en esta PR (sería Fase 2; mucho refactor de compose UI).
- No tocamos el flujo de creación de plato (`/compose`).
- No migramos a `pgvector`/embeddings para related dishes — ILIKE basta para v1.
- No implementamos OCR de menú para correlacionar plato↔ítem de carta (mencionado como pending C5 en restaurants v2).

## Riesgos

- **Costo Claude**: ~83 platos hoy × ~200 tokens output ≈ trivial. Pero el set crecerá; agregar log de generación y cap de regeneración (1× por dish salvo refresh manual).
- **Related dishes ILIKE**: con dataset chico funciona; al crecer, mover a tsvector / pg_trgm. Documentar como migración futura.
- **Move de Lightbox**: tocar imports del restaurant page; verificar no se rompa la pestaña Fotos del restaurante existente.
- **Sticky tabs en mobile**: probar con navbar global ya sticky a `top-0`; los tabs en `top-14` deben respetar la altura real de la navbar en mobile.
