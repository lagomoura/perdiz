# UI components — p3rDiz

Sistema de componentes. Los tokens mencionados acá están definidos en `docs/brand/visual-system.md`. Cualquier componente debe derivarse de tokens; cualquier uso directo de colores hex o tamaños arbitrarios es un bug de revisión.

## Tokens — implementación

`src/styles/tokens.css`:

```css
:root {
  /* Brand */
  --brand-orange-500: 242 106 31;
  --brand-orange-600: 217 85 12;
  --brand-orange-100: 254 231 214;
  --brand-graphite-900: 30 30 30;
  --brand-graphite-700: 58 58 58;

  /* Neutrals */
  --neutral-0: 255 255 255;
  --neutral-50: 247 247 248;
  --neutral-100: 237 237 240;
  --neutral-200: 217 217 222;
  --neutral-400: 156 163 175;
  --neutral-600: 75 85 99;
  --neutral-900: 17 17 19;

  /* State */
  --success-500: 16 185 129;
  --warning-500: 245 158 11;
  --error-500:   239 68 68;
  --info-500:    59 130 246;

  /* Radii */
  --radius-sm: 4px;
  --radius-md: 8px;
  --radius-lg: 12px;
  --radius-xl: 20px;

  /* Shadows */
  --shadow-sm: 0 1px 2px rgb(17 17 19 / 0.06);
  --shadow-md: 0 4px 12px rgb(17 17 19 / 0.08);
  --shadow-lg: 0 12px 32px rgb(17 17 19 / 0.12);
  --shadow-focus: 0 0 0 3px rgb(242 106 31 / 0.35);

  /* Fonts */
  --font-display: 'Space Grotesk', ui-sans-serif, system-ui, sans-serif;
  --font-body:    'Inter', ui-sans-serif, system-ui, sans-serif;
  --font-mono:    'JetBrains Mono', ui-monospace, monospace;
}
```

Tailwind lee estas vars vía `tailwind.config.ts`:

```ts
theme: {
  extend: {
    colors: {
      brand: {
        orange: {
          500: 'rgb(var(--brand-orange-500) / <alpha-value>)',
          600: 'rgb(var(--brand-orange-600) / <alpha-value>)',
          100: 'rgb(var(--brand-orange-100) / <alpha-value>)',
        },
        graphite: {
          900: 'rgb(var(--brand-graphite-900) / <alpha-value>)',
          700: 'rgb(var(--brand-graphite-700) / <alpha-value>)',
        },
      },
      neutral: {
        0:   'rgb(var(--neutral-0) / <alpha-value>)',
        50:  'rgb(var(--neutral-50) / <alpha-value>)',
        100: 'rgb(var(--neutral-100) / <alpha-value>)',
        200: 'rgb(var(--neutral-200) / <alpha-value>)',
        400: 'rgb(var(--neutral-400) / <alpha-value>)',
        600: 'rgb(var(--neutral-600) / <alpha-value>)',
        900: 'rgb(var(--neutral-900) / <alpha-value>)',
      },
      success: { 500: 'rgb(var(--success-500) / <alpha-value>)' },
      warning: { 500: 'rgb(var(--warning-500) / <alpha-value>)' },
      error:   { 500: 'rgb(var(--error-500) / <alpha-value>)' },
      info:    { 500: 'rgb(var(--info-500) / <alpha-value>)' },
    },
    fontFamily: {
      display: 'var(--font-display)',
      body:    'var(--font-body)',
      mono:    'var(--font-mono)',
    },
    borderRadius: { sm: 'var(--radius-sm)', md: 'var(--radius-md)', lg: 'var(--radius-lg)', xl: 'var(--radius-xl)' },
    boxShadow:    { sm: 'var(--shadow-sm)', md: 'var(--shadow-md)', lg: 'var(--shadow-lg)', focus: 'var(--shadow-focus)' },
  },
}
```

## Primitivos (shadcn/ui)

Generar vía CLI de shadcn y ajustar a la estética p3rDiz. Variantes mínimas requeridas:

### Button (`components/ui/Button.tsx`)

Variantes: `primary` (naranja sobre blanco), `secondary` (grafito sobre blanco), `ghost`, `outline`, `destructive`, `link`.
Tamaños: `sm`, `md`, `lg`, `icon`.

```tsx
<Button variant="primary" size="md">Agregar al carrito</Button>
```

Reglas:
- Focus ring naranja (`shadow-focus`) en todas las variantes.
- Loading state: spinner + texto deshabilitado, mantener ancho.
- Nunca usar un `<a>` estilizado como botón ni viceversa; usar `asChild` de Radix para componer.

### Input, Textarea, Select

- Height 40 (sm 32, lg 48).
- Radio md.
- Border `neutral.200`; focus border `brand.orange.500` + `shadow-focus`.
- Errores: border `error.500`, mensaje 12px debajo en `error.500`.

### Checkbox, Switch, Radio

Radix primitives. Color accent `brand.orange.500`. Tamaño 20.

### Dialog, Sheet, Drawer

Radix `Dialog` base.
- Max-width dialog: `lg` (32rem).
- Sheet: para filtros mobile.
- Drawer: para mini-cart.

### Dropdown, Popover, Tooltip

Radix. Fondo `neutral.0`, sombra `md`, border `neutral.100`, radio `md`.

### Toast

`sonner` o equivalente. Posición top-right desktop, top-center mobile.
Variantes: success, error, info, warning. Acciones de undo cuando aplique (ej. "Quitar del carrito" → toast con "Deshacer").

### Tabs, Accordion, Tooltip

shadcn defaults con tokens aplicados.

### Skeleton

Para previews 3D, imágenes, cards durante loading.

### Chip / Badge

- `Chip` (interactivo, p.ej. filtros activos): naranja si activo.
- `Badge` (informativo, p.ej. "Oferta", "Nuevo", estado de pedido): color por variante.

## Componentes de producto

### `ProductCard`

```tsx
<ProductCard
  product={product}
  onAddToCart={() => ...}
  onWishlistToggle={() => ...}
/>
```

Contenido:
- Imagen principal 1:1, lazy.
- Nombre (máx 2 líneas, truncate).
- Precio (si hay descuento: tachado + nuevo precio en naranja).
- Badges de estado (nuevo, oferta, a pedido).
- Botón rápido "Agregar" (oculto hasta hover desktop; siempre visible mobile).
- Toggle wishlist (ícono corazón top-right).

### `ProductGrid`

Responsive: 2 cols mobile, 3 tablet, 4 desktop, 5 en ≥1440. Gap 6 (24px).

### `ProductDetail`

Layout dos columnas desktop: galería izquierda, info derecha. Mobile apilado.

### `ProductGallery`

Thumbnails + preview 3D toggle. Click en thumb cambia imagen; botón "Vista 3D" abre tab adicional.

### `ModelViewer` (3D)

Documentado en `frontend/conventions.md`. Tamaño contenedor: cuadrado en mobile, 4:3 en desktop.

### `CustomizationPanel`

Renderiza `customization_groups` en orden. Cada grupo mapea a un render por tipo vía `features/customization/registry.ts`:

```ts
// registry.ts
export const customizationRenderers: Record<CustomizationType, FC<CustomizationGroupProps>> = {
  COLOR: ColorSwatchGroup,
  MATERIAL: MaterialChipGroup,
  SIZE: SizeChipGroup,
  ENGRAVING_TEXT: EngravingTextField,
  ENGRAVING_IMAGE: EngravingImageUpload,
  USER_FILE: UserFileUpload,
};
```

Cada renderer es independiente; agregar un tipo nuevo = agregar entrada al registro.

### Selectores por tipo

- **ColorSwatchGroup**: swatches circulares 32px, seleccionado tiene ring naranja + check centrado.
- **MaterialChipGroup / SizeChipGroup**: chips rectangulares; seleccionado fondo grafito texto blanco.
- **EngravingTextField**: input + contador + preview live con fuente display.
- **EngravingImageUpload / UserFileUpload**: dropzone; muestra nombre + tamaño + thumb si imagen; botón quitar.

## Componentes de carrito y checkout

### `MiniCart` (drawer)

Desde el ícono del header. Lista items, subtotal, botones "Ver carrito" / "Pagar".

### `CartLineItem`

Imagen thumb, nombre, personalizaciones resumidas ("Color: Rojo · Material: PETG · Texto: «Juan»"), precio unitario, selector cantidad, subtotal, botón eliminar.

### `CheckoutStepper`

3 pasos: Envío, Pago, Confirmación. Navegable hacia atrás.

### `AddressForm`

Con autocomplete de provincia (datalist estático Argentina). Validación postal code numérico.

### `PaymentProviderSelector`

Cards con logo MP / Stripe / PayPal. MercadoPago destacado como recomendado.

## Componentes admin

### `DataTable`

- Columnas configurables.
- Sort server-side (clic en header dispara query param).
- Paginación cursor-based.
- Filtros en toolbar sticky.
- Selección múltiple opcional para acciones bulk.

### `FormShell`

- Header con breadcrumbs + acciones (Guardar / Cancelar / Eliminar).
- Save sticky en mobile.
- Feedback de "Cambios sin guardar" con `beforeunload` warning.

### `ImageManager`

Drag-drop, orden por arrastre, alt text por imagen, botón reemplazar/eliminar. Max 8 imágenes.

### `ModelUploader`

Uploader dedicado para STL. Muestra progreso de subida, luego progreso de conversión STL→GLB (polling al backend), preview 3D al finalizar.

### `CustomizationEditor`

Lista de grupos, cada uno colapsable. Dentro, tabla de opciones editable inline (label, modifier, metadata según tipo, default, available, orden). Botón "Agregar grupo" con selector de tipo.

### `OrderTimeline`

Línea temporal vertical con estados, timestamps, autor del cambio, notas.

### `AuditTrail`

Tabla filtrable con diff visual (before/after JSON), expandible.

### `KpiCard`

Número grande, label, delta vs periodo anterior (flecha + porcentaje verde/rojo), sparkline opcional.

## Layouts

### `PublicLayout`

Header sticky: logo + nav categorías (desktop) / hamburguesa (mobile) + búsqueda + wishlist + carrito + auth.
Footer: 3 columnas (p3rDiz / Ayuda / Legales) + redes + nota país.

### `AccountLayout`

Sidebar con links a secciones del perfil; header común al público.

### `AdminLayout`

Sidebar permanente (desktop) / collapsible (mobile). Topbar con búsqueda global, accesos rápidos, avatar.
Estilo algo más denso: padding 3–4 en vez de 6.

## Estados vacíos

Ilustración low-poly + título + descripción breve + CTA.

Ejemplos:
- Carrito vacío → perdiz caminando: "Tu carrito está vacío. Dale una vuelta al catálogo."
- Sin resultados de búsqueda → lupa low-poly: "Nada por acá. Probá con otra palabra."
- Sin pedidos → caja vacía: "Todavía no hay compras. Cuando encargues, aparecen acá."

Las ilustraciones se entregan como SVGs en `public/illustrations/`; el sistema las referencia por nombre desde un componente `EmptyState`.

## Iconografía

- Librería: **Lucide** (`lucide-react`).
- Tamaños en UI: 16 (inline texto), 20 (botones), 24 (nav, headers).
- Stroke width 1.75 por default.

## Motion

- Transiciones Tailwind estándar `transition`, `duration-200`, easing custom desde config:
  ```ts
  transitionTimingFunction: {
    'in-out-smooth': 'cubic-bezier(0.2, 0.8, 0.2, 1)',
  }
  ```
- **Respetar `prefers-reduced-motion`**: en `globals.css` un media query neutraliza animaciones decorativas.

## Formato

- Moneda (ARS): `Intl.NumberFormat('es-AR', { style: 'currency', currency: 'ARS', maximumFractionDigits: 0 })`. Helper en `lib/format.ts`.
- Fechas: `date-fns` + locale `es`. Formato default `d MMM yyyy` en listados, `EEEE d 'de' MMMM 'de' yyyy · HH:mm` en detalle.
- Números grandes: con separador de miles (`.` en Argentina).

## Accesibilidad — checklist por componente

- `<button>` con texto accesible (texto visible o `aria-label`).
- Inputs siempre con `<label>` asociado (no placeholder-only).
- Diálogos: focus trap, ESC cierra, foco a primer control, al cerrar vuelve al disparador.
- Swatches de color: `aria-label="Color Rojo"`.
- `<img>` con `alt` obligatorio; decorativas `alt=""`.
- Región landmark: `<main>`, `<nav>`, `<footer>` apropiados en cada layout.
