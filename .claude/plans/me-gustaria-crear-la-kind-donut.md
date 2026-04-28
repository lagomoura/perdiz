# Página estrella del Restaurante — Plan de implementación

## Context

CritiComida posiciona al **plato** como protagonista, pero todo plato vive dentro de un restaurante. Hoy `/restaurants/[id]/page.tsx` ya existe como Client Component con Hero, DishChecklist, RatingSection (5 dimensiones), LocationMap y TopReviewsGrid, y el modelo backend ya guarda metadata rica (Google Places: place_id, address, lat/lng, website, phone, opening_hours, price_level + 5 dimensiones agregadas + pros_cons + diary_entries + menu).

El objetivo es **convertir esta página en la página estrella del proyecto, junto con el feed**: muy informativa, bonita, llamativa, alimentada por reviews + Google Maps + agregaciones derivadas. Decisiones del usuario: alcance Fases A+B+C, **layout con tabs** (Resumen / Platos / Reseñas / Fotos / Info), y refactor a **Server Component** con islas client para interacción.

Estrategia tabs + SSR: el server fetcha TODOS los datos una sola vez (Promise.all), los pasa como props a un cliente `<RestaurantTabs />` que controla visibilidad con `hidden` attribute o `display:none`. Así Google ve todo el HTML inicial (SEO óptimo) y el usuario percibe tabs instantáneos sin navegación.

---

## Fase A — Rediseño con datos existentes (MVP visible)

### Endpoints backend nuevos

Archivo: `backend/app/routers/restaurants.py` + schemas en `backend/app/schemas/restaurant.py`.

| Endpoint | Retorna | Lógica |
|---|---|---|
| `GET /api/restaurants/{slug}/aggregates` | `pros_top[]`, `cons_top[]`, `dimension_averages{}`, `dimension_breakdown_count{}`, `photos_count`, `dishes_count` | GROUP BY sobre `restaurant_pros_cons` y `restaurant_dimension_ratings`, ordenado por count desc, limit 8. |
| `GET /api/restaurants/{slug}/photos?limit=24&cursor=` | `items[]:{url, taken_at, dish_id, dish_name, user_id, user_handle}`, `next_cursor` | JOIN `dish_reviews` → `dishes` WHERE restaurant_id, image_url IS NOT NULL, ORDER BY created_at DESC, paginado por cursor. |
| `GET /api/restaurants/{slug}/diary-stats` | `unique_visitors`, `visits_last_7d`, `avg_spent`, `most_ordered_dish:{id,name}`, `recent_visitors[8]:{id,handle,avatar}` | SQL agregado sobre `visit_diary_entries`. |
| `GET /api/restaurants/{slug}/signature-dishes?limit=4` | `dishes[]:{id,name,cover_image_url,computed_rating,review_count,best_quote}` | Top dishes por `computed_rating` con `best_quote` = nota más reciente de reseña 5★. |

### Refactor a Server Component

`app/restaurants/[id]/page.tsx`:
- Pasa a `async function Page({ params })`, fetch paralelo con `Promise.all` de detail + aggregates + photos + diary-stats + signature-dishes + dishes list.
- `generateMetadata` con OG image = `cover_image_url`, title `${restaurant.name} · CritiComida`, description editorial.
- Renderiza shell server: `<HeroV2 />` + `<RestaurantTabs />` (cliente) recibiendo todos los datos como props.

Nuevos archivos hermanos:
- `app/restaurants/[id]/loading.tsx` — skeleton del hero + barra de tabs.
- `app/restaurants/[id]/not-found.tsx` — vacío editorial con CTA "Buscar otro".

### Componentes nuevos (en `app/restaurants/[id]/components/`)

- **`HeroV2.tsx`** (server): cover full-bleed h-96, overlay gradient azafrán→carbón, breadcrumb (categoría · ciudad), nombre Cormorant 5xl, chips meta (categoría · price_level $$$ · `OpenStatus`), rating compuesto + nº reseñas + nº platos, CTAs (Agregar plato páprika · Guardar outline · Compartir icon), avatar creator "Curado por @x".
- **`RestaurantTabs.tsx`** (client): controla qué sección está visible. URL state via `?tab=` con `useSearchParams` + `router.replace` shallow. Pills sticky en mobile. Tabs: Resumen, Platos, Reseñas, Fotos, Info.
- **`tabs/ResumenTab.tsx`** (server): contiene `RatingsRadar` + `ProsConsAggregated` + `SignatureDishes` + `DiaryPulse` + `RestaurantRatingSection` (input editable existente).
- **`tabs/PlatosTab.tsx`** (server): `DishChecklist` existente envuelto + grid completo.
- **`tabs/ReseñasTab.tsx`** (server): `TopReviewsCarousel` (extiende TopReviewsGrid) + lista paginada de todas las reseñas.
- **`tabs/FotosTab.tsx`** (client): `PhotoMosaic` masonry, abre `Lightbox` existente.
- **`tabs/InfoTab.tsx`** (server): `InfoPanel` (dirección, teléfono click-to-call, website, Google Maps button, tabla horarios resaltando hoy) + `LocationMap` h-80 + `MenuSection` si existe menú.
- **`RatingsRadar.tsx`** (server): SVG inline con 5 dimensiones + barras horizontales con conteo. Sin libs externas.
- **`ProsConsAggregated.tsx`** (server): 2 columnas, chips Albahaca para pros, Páprika para cons, con `(count)`.
- **`SignatureDishes.tsx`** (server): grid 2x2 desktop / scroll horizontal mobile. Reusa estructura de `PlateCard`.
- **`PhotoMosaic.tsx`** (client): masonry CSS columns, lazy loading, abre Lightbox existente.
- **`DiaryPulse.tsx`** (server): stats de diario + avatares recent_visitors.
- **`InfoPanel.tsx`** (server): dirección + horarios.
- **`OpenStatus.tsx`** (client): pequeño badge "Abierto · cierra 23:00" / "Cerrado · abre mañana 12:00", calculado desde `opening_hours` en cliente para usar zona horaria del visitante.
- **`RestaurantActionsBar.tsx`** (client): botones Guardar/Compartir/Agregar plato, con estado optimista para Guardar.

### Util nuevo

`app/lib/utils/openingHours.ts`:
- `parseOpeningHours(json: GoogleOpeningHours, now: Date): { isOpen, closesAt?, opensAt? }`.
- Maneja overnight (cierra después de medianoche), días sin horario, formato Google Places.

### API client + tipos

`app/lib/api/restaurants.ts` agregar:
- `getRestaurantAggregates(slug)`, `getRestaurantPhotos(slug, params)`, `getDiaryStats(slug)`, `getSignatureDishes(slug, limit)`.

`app/lib/types/restaurant.ts` agregar:
- `RestaurantAggregates`, `DiaryStats`, `SignatureDish`, `RestaurantPhoto`, `OpenStatusInfo`.

### Tokens visuales

- Hero: gradient `linear-gradient(180deg, transparent 0%, var(--color-carbon) 100%)`.
- CTAs primarios: `--color-azafran` (Guardar/Agregar).
- Rating ≥ 9: `--color-albahaca`. Errores/cons: `--color-paprika`.
- Tipografía: `--font-cormorant` para H1/H2 + quotes; `--font-dm-sans` para meta/UI.

### Orden de implementación Fase A

1. Backend: schemas → 4 endpoints nuevos → tests pytest.
2. Frontend: tipos TS → API client.
3. Util `openingHours.ts` con tests.
4. Componentes server (HeroV2, RatingsRadar, ProsConsAggregated, SignatureDishes, DiaryPulse, InfoPanel, tabs/*).
5. Componentes client (RestaurantTabs, PhotoMosaic, OpenStatus, RestaurantActionsBar).
6. Refactor `page.tsx` a server component, `loading.tsx`, `not-found.tsx`.
7. Verificación visual con Playwright MCP.

---

## Fase B — Enriquecimiento Google Places

### Migration alembic 014 — `restaurant_google_enrichment`

Archivo: `backend/alembic/versions/014_restaurant_google_enrichment.py`. Campos en `restaurants`:
- `google_rating NUMERIC(2,1)`, `google_user_ratings_total INTEGER`
- `google_photos JSONB` — lista `[{photo_reference, width, height, attribution_html, cached_url}]`
- `editorial_summary TEXT`, `editorial_summary_lang VARCHAR(8)`
- `cuisine_types TEXT[]`
- `google_cached_at TIMESTAMPTZ`, `google_cache_ttl_hours INTEGER DEFAULT 168`

### Estrategia: lazy fetch + cache + background refresh

- En `GET /api/restaurants/{slug}`: si `google_place_id IS NOT NULL` y cache vencido, encolar `BackgroundTasks` para refrescar; sirve datos cacheados (o no enriquecidos en primer hit).
- Worker `backend/app/services/google_places_enricher.py`: llama Places Details (`fields=rating,user_ratings_total,editorial_summary,photos,types`), descarga primeras 6 fotos a storage propio (Vercel Blob o S3, evita expirar URLs Places y respeta TOS de attribution), persiste `cached_url + attribution_html`.
- Storage: `backend/app/services/google_photos_storage.py`.
- Endpoint manual: `POST /api/restaurants/{slug}/refresh-google` (admin/critic) — fuerza refresh sincrónico.
- Rate limit: `asyncio.Semaphore(4)` global.

### Frontend Fase B

- `HeroV2`: dual-rating "CritiComida 4.6 · Google 4.3 (1.2k)" con tooltip explicativo.
- `EditorialSummaryCard.tsx` (server, nuevo): párrafo Cormorant italic con atribución "vía Google" en `ResumenTab`.
- `PhotoMosaic`: mezcla UGC + google_photos con badge sutil de origen.
- Chips `cuisine_types` en hero junto a categoría.

### Orden Fase B

Migration → modelo SQLAlchemy → enricher service → photos storage → endpoint refresh → tipos TS → componentes UI. Independiente de Fase A salvo reuso de `HeroV2` y `PhotoMosaic`.

---

## Estado de implementación (2026-04-27)

- ✅ **Fase A** completada y verificada: 4 endpoints de agregación, refactor a Server Component, todos los componentes (HeroV2, RatingsRadar, ProsConsAggregated, SignatureDishes, DiaryPulse, InfoPanel, PhotoMosaic, OpenStatus, RestaurantTabs, RestaurantActionsBar, RestaurantPageClient), util openingHours, loading.tsx, not-found.tsx. Tests integration en `tests/integration/test_restaurant_aggregates.py`. Backend Docker rebuildeado, datos reales fluyen.
- ✅ **Fase B** entregada (infra completa): migration `014_restaurant_google_enrichment.py` aplicada (campos google_rating, google_user_ratings_total, google_photos JSONB, editorial_summary, cuisine_types, google_cached_at), modelo + schema actualizados, servicio `google_places_enricher.py` con cache TTL + lazy refresh + endpoint manual `POST /{slug}/refresh-google`, frontend dual rating en HeroV2 + cuisine chips + EditorialSummaryCard + PhotoMosaic mezclado UGC/Google. **Faltante**: agregar `GOOGLE_PLACES_API_KEY` al .env del backend para activar el enrichment real (servicio degrada silencioso sin clave).
- ✅ **Fase C parcial**: C1 (geolocation hook `useUserLocation` + `DistanceBadge` en hero) y C2 (`GET /{slug}/nearby` con Haversine en SQL + `NearbyRestaurantsCarousel`) — entregadas y verificadas con datos reales. **Pendientes documentadas abajo**: C3 popular times (requiere lib externa), C4 social diary (integración bookmarks API), C5 menu OCR (worker separado).

## Fase C — Avanzado

### C1: Distancia desde el usuario

- `app/lib/hooks/useUserLocation.ts` (client): `navigator.geolocation` con permission gate y fallback ciudad.
- Badge "A 1.2 km" en `HeroV2` (cliente, hidratado tras geolocation).

### C2: Restaurantes cercanos

- Migration 015: extensión `cube` + `earthdistance` (Postgres nativo, sin PostGIS) o índice geoespacial simple.
- Endpoint `GET /api/restaurants/{slug}/nearby?radius_km=2&limit=6` — `earth_distance(ll_to_earth(...))`.
- Componente `NearbyRestaurantsCarousel.tsx` al final del `ResumenTab` y propio en `InfoTab`.

### C3: Popular times

- Lib `populartimes` (scraper no oficial, disclaimer legal). Worker scheduled diario.
- Campo `popular_times JSONB` en restaurants.
- Componente `PopularTimesChart.tsx` (client, gráfico de barras 24h x 7d) en `InfoTab`.

### C4: Diario social

- Endpoint `GET /api/restaurants/{slug}/social-visits?friends_only=true` — JOIN follows + visit_diary_entries.
- En `DiaryPulse`: sección "Tus contactos también vinieron" con avatares de quienes el usuario sigue que han registrado visitas.
- "Guardar" abre modal con listas guardadas (reusa bookmarks API existente).

### C5: Menú renderizado estructurado

- Worker OCR (Tesseract o Google Cloud Vision) sobre `menu.image_url` → entries estructuradas.
- Tabla nueva `menu_entries(id, menu_id, name, description, price)`.
- `MenuSection` extendido con búsqueda de plato dentro del menú.

---

## Critical files

### Backend
- `backend/app/routers/restaurants.py` — 4 endpoints A + 1 endpoint B + 1 endpoint C2.
- `backend/app/schemas/restaurant.py` — schemas response.
- `backend/app/models/restaurant.py` — campos B + C3.
- `backend/alembic/versions/014_restaurant_google_enrichment.py` — Fase B.
- `backend/alembic/versions/015_earthdistance_extension.py` — Fase C2.
- `backend/app/services/google_places_enricher.py` — Fase B.
- `backend/app/services/google_photos_storage.py` — Fase B.

### Frontend
- `app/restaurants/[id]/page.tsx` — refactor server.
- `app/restaurants/[id]/loading.tsx` (nuevo).
- `app/restaurants/[id]/not-found.tsx` (nuevo).
- `app/restaurants/[id]/components/HeroV2.tsx` (nuevo, reemplaza `RestaurantHero`).
- `app/restaurants/[id]/components/RestaurantTabs.tsx` (nuevo).
- `app/restaurants/[id]/components/tabs/{Resumen,Platos,Reseñas,Fotos,Info}Tab.tsx` (5 nuevos).
- `app/restaurants/[id]/components/{RatingsRadar,ProsConsAggregated,SignatureDishes,PhotoMosaic,DiaryPulse,InfoPanel,OpenStatus,RestaurantActionsBar,EditorialSummaryCard,NearbyRestaurantsCarousel,PopularTimesChart}.tsx`.
- `app/lib/api/restaurants.ts` — funciones nuevas.
- `app/lib/types/restaurant.ts` — tipos nuevos + campos google_*.
- `app/lib/utils/openingHours.ts` (nuevo).
- `app/lib/hooks/useUserLocation.ts` (nuevo, Fase C1).

### Existentes a reusar (no tocar lógica, solo importar)
- `app/restaurants/[id]/components/{PlateCard,DishChecklist,Lightbox,PhotoGallery,StarRating,ProsCons,DishReviewForm,RestaurantRatingSection,TopReviewsGrid,LocationMap,AddDishModal}.tsx`.
- `app/components/ui/{Button,Badge,Avatar,Chip,Tabs,EmptyState,Skeleton}.tsx`.
- `app/components/maps.tsx`.
- `app/components/social/RestaurantAutocomplete.tsx`.
- `app/lib/api/client.ts` — `fetchApi`.

---

## Verificación end-to-end

1. **Backend**: `npm run test:backend` con tests para los 4 endpoints A + endpoint B refresh + endpoint C2 nearby. Fixtures con restaurante real (place_id válido, dimension_ratings, pros_cons, diary_entries, dishes con reseñas con imágenes).
2. **Frontend types**: `npm run lint` + `tsc --noEmit` (vía build).
3. **Visual con Playwright MCP** (`mcp__playwright-mcp__*`):
   - Navegar a `http://localhost:3000/restaurants/{slug}` (slug real de seed, ver `project_db_state.md` — 83 restaurantes reales).
   - Snapshot del hero, validar nombre/rating/CTAs visibles.
   - Click en cada tab (Resumen, Platos, Reseñas, Fotos, Info), verificar que `?tab=` actualiza URL y contenido cambia.
   - Validar `OpenStatus` muestra estado coherente vs `opening_hours`.
   - Click en foto → Lightbox abre.
   - Mobile viewport: validar pills sticky y mosaico responsive.
4. **SEO/SSR**: `curl http://localhost:3000/restaurants/{slug}` y verificar que el HTML inicial incluye nombre, descripción y todas las secciones (no spinner).
5. **Build**: `npm run build` — sin warnings de "use client" en page.tsx.
6. **Manual**: con backend corriendo (`http://localhost:8000`), recorrer flujo completo agregar plato → ver aparece en `SignatureDishes` si rating alto → ver foto en `PhotoMosaic`.

---

## Notas de implementación

- **No tocar** `compose/ComposeClient.tsx` ni `RestaurantAutocomplete` — el flujo de creación de restaurantes desde Google Places ya funciona.
- **Mock flag**: respetar el flag de mock data documentado en `project_social_migration.md` Fase 0; los endpoints nuevos deben tener fallback en `app/data/` para cuando el backend está caído.
- **Slug vs id**: el routing actual es `[id]` pero el backend usa `slug`. Confirmar si `[id]` ya está siendo tratado como slug o si hay que renombrar la ruta a `[slug]`. **Decisión preferida**: mantener `[id]` como segmento que acepta slug (URL bonita) — sin breaking change.
- **Imágenes**: usar `next/image` con `remotePatterns` configurado para el storage de fotos Google cacheadas (Fase B).
- **Accesibilidad**: tabs con `role="tablist"`, `aria-selected`, navegación con teclado (←/→). Lightbox con focus trap.
- **Performance**: la página tiene muchas secciones — usar `<Suspense>` por tab para streaming progresivo si los fetch son lentos.
