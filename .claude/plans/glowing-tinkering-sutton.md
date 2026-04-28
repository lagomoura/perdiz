# Plan: Flujo de creación de categorías en AddRestaurantModal

## Context

El problema real: cuando se agrega un restaurante cuya categoría no existe, no hay un flujo real — "Otros" era un parche que asigna los restaurantes en un limbo sin señal clara para los admins. El objetivo es:

1. Ocultar "Otros" de la vista pública (home, filtros) — es una categoría interna de staging.
2. Dar a los **admins** un flujo inline para crear la categoría nueva directamente al agregar el restaurante, con imagen generada por IA.
3. Los usuarios no-admin siguen usando las categorías existentes; "Otros" como asignación interna sigue funcionando en DB (los restaurantes existentes no se rompen).

---

## Part 1: Ocultar "Otros" de la UI pública

**Archivo:** `app/components/ReviewsSection.tsx`

- Filtrar `slug === 'otros'` al construir los cards de categoría y las opciones del filtro.
- Un comentario explica que "otros" es categoría interna.

---

## Part 2: Flujo inline de nueva categoría en `AddRestaurantModal`

### Estado nuevo en el modal

```ts
const [newCategoryName, setNewCategoryName] = useState('');
const [creatingCategory, setCreatingCategory] = useState(false); // modo "nueva cat"
const [categoryImageUrl, setCategoryImageUrl] = useState<string | undefined>();
const [generatingImage, setGeneratingImage] = useState(false);
const [duplicateWarning, setDuplicateWarning] = useState<Category | null>(null);
```

### Cambios en el selector de categoría

- El `<select>` muestra solo categorías "reales" (excluye `slug === 'otros'`).
- Para admins (`user.role === 'admin'`): aparece debajo del select un link/botón `+ Nueva categoría`.
- Al hacer click se muestra un `<input type="text">` para escribir el nombre.

### Panel inline de preview (visible cuando hay nombre escrito)

```
┌──────────────────────────────────────────┐
│ 📂 Nueva: "Italiana"                     │
│ slug: italiana                           │
│ 🖼 [preview 80x80]  [↻ Re-generar]       │
│ ✓ Sin duplicados                         │  <- o ⚠ "¿Quisiste decir Mexicana?"
└──────────────────────────────────────────┘
```

- **Duplicate check:** comparación case-insensitive contra `categories` ya cargadas. Si hay match exacto o muy similar → advertencia con botón para usar la existente.
- **Slug:** auto-generado (`toLowerCase().replace(/ /g, '-').normalize('NFD')...`).
- **Imagen:** se genera automáticamente al escribir (debounce 600ms) → llama al endpoint de generación.

### Endpoint de generación de imágenes

**Archivo nuevo:** `app/api/generate-category-image/route.ts`  
(Excepción pragmática a la regla "sin API routes" — es lógica de utilidad, no de negocio)

```ts
// POST { name: "Italiana" }
// → llama fal.ai FLUX o similar
// → devuelve { imageUrl: "..." }
```

- Requiere `FAL_API_KEY` (o `REPLICATE_API_TOKEN`) en `.env`.
- El prompt de imagen: `"Food category cover photo for [name] cuisine, top view, professional food photography, vibrant colors"`.
- Si falla la generación → devuelve `null`, el usuario puede ignorar y crear la categoría sin imagen.

### API function nueva

**Archivo:** `app/lib/api/categories.ts`

```ts
export async function createCategory(data: {
  name: string; slug: string; image_url?: string;
}): Promise<Category> {
  return fetchApi<Category>('/api/categories', { method: 'POST', body: JSON.stringify(data) });
}
```

### Submit del modal con nueva categoría

```
handleSubmit:
  1. if (creatingCategory && newCategoryName):
       a. POST /api/categories → obtiene newCat
       b. POST /api/restaurants con category_id = newCat.id
  2. else: flujo actual
```

- Si el `POST /api/categories` retorna 409 (ya existe) → mostrar error + sugerir cambiar al existente.
- Si retorna 403 → no debería pasar (el botón solo aparece a admins), pero mostrar error genérico.

---

## Archivos a modificar / crear

| Archivo | Cambio |
|---|---|
| `app/components/ReviewsSection.tsx` | Filtrar `slug === 'otros'` |
| `app/reviews/[category]/AddRestaurantModal.tsx` | Flujo nueva categoría |
| `app/lib/api/categories.ts` | Agregar `createCategory()` |
| `app/api/generate-category-image/route.ts` | **Nuevo** — endpoint de generación de imagen |
| `.env` | Agregar `FAL_API_KEY` o `REPLICATE_API_TOKEN` |

**No se modifica:** el backend FastAPI ni la DB. "Otros" sigue en DB para los restaurantes existentes.

---

## Variable de entorno para imagen

Usar **fal.ai** como proveedor (tiene SDK JS, free tier, modelo FLUX-schnell):
```
FAL_KEY=...
```

Si el usuario no configura la key, la generación de imagen simplemente no ocurre y el panel muestra un placeholder — la categoría se puede crear sin imagen.

---

## Verificación

1. `npm run dev` — abrir home, confirmar que "Otros" no aparece en cards ni filtros.
2. Loguear como admin → ir a cualquier `/reviews/[category]` → "Agregar restaurante" → verificar que aparece botón "+ Nueva categoría".
3. Escribir "Italiana" → ver que el panel aparece, slug se genera, imagen se carga.
4. Escribir una categoría ya existente (ej: "Mexicana") → verificar advertencia de duplicado.
5. Submit → confirmar que la categoría se crea y el restaurante queda asignado.
6. Loguear como usuario no-admin → confirmar que el botón "+ Nueva categoría" no aparece.
