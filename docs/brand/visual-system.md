# Sistema visual — Aura

Sistema de diseño. Todo componente en `apps/web` debe derivarse de estos tokens. Cualquier color, radio, sombra o tamaño fuera de los tokens es un bug.

## Logo

**Archivo principal**: `apps/web/public/brand/logo.png`.
**Favicons derivados**: `favicon.ico` (32×32 multi-res), `favicon-180.png` (apple-touch), `favicon-192.png`, `favicon-512.png`.
**Fuente original**: `/source/aura_logo.png` (referenciar si se requiere para regenerar variantes; no usar en build directamente).

**Composición del logo**:
- **Isotipo**: la letra "A" estilizada con boquilla de impresora 3D arriba, sobre un disco oscuro con halo de gradiente rojo-naranja → amarillo.
- **Logotipo**: "AURA" en versalitas, color claro con leve sombreado, sobre placa oscura.
- **Descriptor**: "IMPRESIONES 3D" en versalitas chicas, debajo de "AURA".

**Variantes a producir cuando haga falta**:
1. **Principal** — composición completa sobre fondo oscuro o claro.
2. **Horizontal** — isotipo a la izquierda, "AURA / IMPRESIONES 3D" a la derecha (para headers).
3. **Isotipo solo** — favicon, app icon, avatares de redes.
4. **Monocromo grafito** — fondos muy claros donde el naranja distrae.
5. **Monocromo blanco** — fondos oscuros sólidos.

**Zona de respeto**: mínimo equivalente a la altura del isotipo en los cuatro lados.

**Tamaños mínimos**:
- Web/digital: 64px de alto para el isotipo; el logo completo ya viene cuadrado y se renderiza a `h-28` o más en headers (ver `Header.tsx`).
- Favicon: `favicon.ico` 32×32 — el detalle de la boquilla se pierde por debajo, evitar tamaños menores.

**No hacer**: distorsionar, reemplazar tipografías, invertir colores de forma arbitraria, encerrar en marcos, aplicar sombras o degradados al logo.

## Paleta de color

### Primarios

| Token | Hex | Uso |
|---|---|---|
| `brand.orange.500` | `#E94E1B` | Color primario. CTAs, acentos, estados activos. |
| `brand.orange.600` | `#C43C12` | Hover / pressed sobre el primario. |
| `brand.orange.100` | `#FDE0D3` | Fondos suaves de énfasis, chips. |
| `brand.amber.500` | `#F4B41A` | Acento amarillo del gradiente Aura. Detalles, badges, highlights. |
| `brand.amber.600` | `#D4980E` | Hover sobre amber. |
| `brand.graphite.900` | `#1E1E1E` | Tipografía principal, iconografía, headers oscuros. |
| `brand.graphite.700` | `#3A3A3A` | Tipografía secundaria. |

### Neutros

| Token | Hex | Uso |
|---|---|---|
| `neutral.0` | `#FFFFFF` | Fondo base. |
| `neutral.50` | `#F7F7F8` | Fondos de superficie (cards, secciones alternas). |
| `neutral.100` | `#EDEDF0` | Bordes suaves, divisores. |
| `neutral.200` | `#D9D9DE` | Bordes medianos. |
| `neutral.400` | `#9CA3AF` | Texto deshabilitado, placeholders. |
| `neutral.600` | `#4B5563` | Texto secundario sobre blanco. |
| `neutral.900` | `#111113` | Alias de grafito para modo oscuro. |

### Estado

| Token | Hex | Uso |
|---|---|---|
| `state.success.500` | `#10B981` | Confirmaciones, pedidos entregados. |
| `state.warning.500` | `#F59E0B` | Stock bajo, advertencias. |
| `state.error.500` | `#EF4444` | Errores, cancelaciones. |
| `state.info.500` | `#3B82F6` | Información neutra, notas. |

Cada color de estado tiene variantes `.100` (fondo suave) y `.700` (texto sobre fondo suave) para banners.

### Contraste

Todo par texto/fondo debe cumplir **WCAG AA** (4.5:1 mínimo en texto normal, 3:1 en texto grande/iconos). El naranja `#E94E1B` sobre blanco **no cumple AA para texto chico**; usarlo solo en botones/CTAs con texto blanco encima o en texto ≥18px bold. El amarillo `#F4B41A` directamente nunca debe llevar texto encima — usar solo como acento decorativo o como background con texto graphite-900.

## Tipografía

- **Display / Titulares**: **Space Grotesk** (400, 500, 700). Usar en H1–H3, precios destacados, números de estado.
- **Body / UI**: **Inter** (400, 500, 600, 700). Usar en párrafos, labels, tablas, botones.
- **Mono** (código admin, SKUs, IDs): **JetBrains Mono** (400, 500).

Fuente desde Google Fonts vía `<link>` con `display=swap`. Self-hostear en producción vía `fontsource` para evitar layout shift.

### Escala

| Rol | Size / Line-height | Peso | Fuente |
|---|---|---|---|
| Display XL (hero) | 64 / 72 | 700 | Space Grotesk |
| H1 | 48 / 56 | 700 | Space Grotesk |
| H2 | 36 / 44 | 700 | Space Grotesk |
| H3 | 28 / 36 | 500 | Space Grotesk |
| H4 | 22 / 30 | 500 | Space Grotesk |
| Body L | 18 / 28 | 400 | Inter |
| Body M (default) | 16 / 24 | 400 | Inter |
| Body S | 14 / 20 | 400 | Inter |
| Caption | 12 / 16 | 500 | Inter |
| Mono | 14 / 20 | 400 | JetBrains Mono |

Responsive: en mobile, bajar Display XL a 44, H1 a 36, H2 a 28.

## Espaciado

Sistema **4px base**. Tokens:

```
0  → 0
1  → 4px
2  → 8px
3  → 12px
4  → 16px
5  → 20px
6  → 24px
8  → 32px
10 → 40px
12 → 48px
16 → 64px
20 → 80px
24 → 96px
```

Componentes internos usan múltiplos bajos (1–6). Secciones/landings usan 12–24.

## Radios

Geometría coherente con el low-poly: radios **moderados**, nunca totalmente redondos excepto en avatares.

| Token | Valor | Uso |
|---|---|---|
| `radius.none` | 0 | Imágenes producto (cuadradas) |
| `radius.sm` | 4px | Inputs, chips |
| `radius.md` | 8px | Botones, cards |
| `radius.lg` | 12px | Dialogs, paneles |
| `radius.xl` | 20px | Hero elements |
| `radius.full` | 9999px | Avatares, dots de estado |

## Sombras

Sutilidad. Nada de sombras suaves flotando: preferimos **bordes + sombra mínima**.

| Token | Valor |
|---|---|
| `shadow.none` | none |
| `shadow.sm` | `0 1px 2px rgba(17,17,19,0.06)` |
| `shadow.md` | `0 4px 12px rgba(17,17,19,0.08)` |
| `shadow.lg` | `0 12px 32px rgba(17,17,19,0.12)` |
| `shadow.focus` | `0 0 0 3px rgba(233,78,27,0.35)` (outline naranja para foco accesible) |

## Iconografía

- Librería: **Lucide** (`lucide-react`). Coherente con shadcn/ui, stroke 1.75.
- Tamaños: 16, 20, 24 px. Nunca escalar fuera de múltiplos de 4.
- Color: hereda de `currentColor`. En UI normal, `neutral.600`; en estados activos, `brand.orange.500`.

**Iconografía de marca** (ilustraciones low-poly): usar con moderación en hero, empty states, confirmaciones de pedido. Mismo lenguaje facetado que el logo, sombreado en escala de grises, acento naranja puntual.

## Imágenes de producto

- Fondo **neutro claro** (`#F7F7F8`) o blanco puro, según la pieza.
- Relación **1:1** en grid, **4:3** en detalle.
- Iluminación uniforme, sin sombras duras que sugieran un tono informal.
- Al menos 1 foto de contexto por producto cuando aplique (mostrar escala con mano, escritorio, etc.).
- WebP para producción, JPEG fallback. Nunca PNG salvo que tenga transparencia.

## Motion

- **Duración**: 120ms (micro), 200ms (transiciones normales), 350ms (entradas/salidas complejas).
- **Easing**: `cubic-bezier(0.2, 0.8, 0.2, 1)` para entradas, `cubic-bezier(0.4, 0, 1, 1)` para salidas.
- **Respetar `prefers-reduced-motion`**: desactivar parallax, rotaciones de preview 3D no interactivas, y animaciones decorativas.

## Tokens — implementación

Los tokens viven en `apps/web/src/styles/tokens.css` como CSS variables y se exponen a Tailwind vía `tailwind.config.ts`. Un cambio de valor se hace en **un solo archivo**. Ver `frontend/ui-components.md` para detalles.
