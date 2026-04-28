# Plan: Sección de valoración del establecimiento en `/restaurants/[id]`

## Context
Los usuarios pueden valorar platos individualmente, pero no el establecimiento en sí (limpieza, ambiente, servicio, etc.). El backend ya tiene todo implementado:
- Modelo `RestaurantRatingDimension` con 5 dimensiones: `cleanliness`, `ambiance`, `service`, `value`, `food_quality`
- `GET /api/restaurants/{slug}/ratings` → devuelve promedios por dimensión + breakdown por usuario
- `PUT /api/restaurants/{slug}/ratings` → upsert de ratings del usuario autenticado
- `update_restaurant_rating` ya combina platos + dimensiones: `avg(dishes)*0.5 + avg(dims)*0.5`

**Solo hay que construir el frontend.**

---

## Archivos a crear/modificar

| Archivo | Acción |
|---|---|
| `app/lib/types/restaurant.ts` | Agregar `RatingDimensionKey`, `RestaurantRatingsResponse` |
| `app/lib/types/index.ts` | Exportar nuevos tipos |
| `app/lib/api/ratings.ts` | Crear: `getRestaurantRatings`, `setRestaurantRatings` |
| `app/restaurants/[id]/components/RestaurantRatingSection.tsx` | Crear: sección completa |
| `app/restaurants/[id]/components/index.ts` | Exportar nuevo componente |
| `app/restaurants/[id]/page.tsx` | Agregar `<RestaurantRatingSection>` entre DishChecklist y LocationMap |

---

## Detalle de implementación

### 1. Tipos (`app/lib/types/restaurant.ts`)

```typescript
export type RatingDimensionKey = 'cleanliness' | 'ambiance' | 'service' | 'value' | 'food_quality';

export interface RestaurantRatingsResponse {
  restaurant_id: string;
  averages: Partial<Record<RatingDimensionKey, number>>;
  user_breakdown: Record<string, {
    dimension: RatingDimensionKey;
    score: number;
    user_display_name: string;
  }[]>;
}
```

### 2. API (`app/lib/api/ratings.ts`) — nuevo archivo

```typescript
getRestaurantRatings(slug): Promise<RestaurantRatingsResponse>
  // GET /api/restaurants/{slug}/ratings

setRestaurantRatings(slug, ratings: {dimension, score}[]): Promise<void>
  // PUT /api/restaurants/{slug}/ratings
```

### 3. Componente `RestaurantRatingSection.tsx`

**Props:**
```typescript
{
  restaurantSlug: string;
  currentUserId: string | null;
}
```

**Lógica:**
- Fetch `getRestaurantRatings(slug)` al montar
- Estado: `ratingsData`, `userRatings` (las 5 dims del usuario actual, pre-rellenas desde `user_breakdown[currentUserId]`), `submitting`, `saved`

**UI — dos partes:**

**Parte A — Promedios (visible a todos):**
- Por cada dimensión con datos: label en español + barra de progreso + número
- Si no hay datos: mensaje "Todavía no hay valoraciones"
- Mapa de labels: `cleanliness→Limpieza`, `ambiance→Ambiente`, `service→Servicio`, `value→Precio/calidad`, `food_quality→Calidad de comida`

**Parte B — Formulario del usuario (solo autenticado):**
- Título: "Tu valoración"
- 5 filas: label + `StarRating` interactivo (reusar componente existente)
- Pre-rellena con los valores del usuario si ya valoró
- Botón "Guardar valoración" → llama `setRestaurantRatings` → actualiza `ratingsData` local
- Si no autenticado: mensaje "Logueate para valorar el establecimiento"

### 4. Integración en `page.tsx`

Agregar entre `<DishChecklist>` y `<LocationMap>`:
```tsx
<RestaurantRatingSection
  restaurantSlug={id}
  currentUserId={user?.id ?? null}
/>
```

---

## Verificación

1. Ir a `/restaurants/chichilo` sin sesión → se ve la sección de promedios (vacía o con datos) y un mensaje de "logueate para valorar"
2. Loguearse como `admin@criticomida.com` → aparece el formulario con 5 StarRatings
3. Poner ratings y guardar → se actualizan las barras de promedio
4. Recargar la página → los ratings del usuario están pre-rellenos
5. Editar un rating y guardar → el promedio cambia
6. El `computed_rating` del restaurante en el hero se actualiza en el próximo load (combina platos + dims)
