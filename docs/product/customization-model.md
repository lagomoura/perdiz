# Modelo de personalización — Aura

Modelo de datos y UX para personalizaciones de producto. Diseñado para **agregar tipos nuevos sin migrar schema** (el campo `type` es enum extensible + validador plugable).

## Jerarquía conceptual

```
Product
  └─ CustomizationGroup (0..N)   ej: "Color", "Material", "Grabado"
       └─ CustomizationOption (1..N)   ej: "Rojo", "Azul", "PLA", "PETG"
            ├─ price_modifier (entero, centavos ARS; puede ser 0 o negativo)
            ├─ is_default (bool)
            └─ metadata (JSONB, depende del tipo)
```

- Cada **grupo** tiene un `type` que determina cómo se renderiza y valida.
- Cada **grupo** tiene `required` (bool) y `selection_mode` (`single` | `multiple`).
- Las opciones **siempre pertenecen a un grupo**; no existen opciones sueltas.

## Tipos soportados en el MVP

### `COLOR`

- Render UI: **swatches** circulares con el color.
- `selection_mode`: `single`.
- Metadata de la opción: `{ "hex": "#FF0000", "label": "Rojo" }`.
- Ejemplo: grupo "Color del filamento" con opciones Rojo, Azul, Negro, Blanco.

### `MATERIAL`

- Render UI: chips con nombre y descripción corta al hover.
- `selection_mode`: `single`.
- Metadata de la opción: `{ "label": "PETG", "description": "Resistente al calor y más duradero que PLA.", "icon": "material-petg" }`.

### `SIZE`

- Render UI: chips con label (ej. "S", "M", "L") o con dimensiones ("10 cm", "15 cm").
- `selection_mode`: `single`.
- Metadata: `{ "label": "Mediano", "dimensions_mm": [100, 100, 50] }` (dimensiones opcionales, informativas).

### `ENGRAVING_TEXT`

- Render UI: input de texto con contador de caracteres y preview.
- `selection_mode`: **implícito single** (un único grupo de este tipo por producto genera un único valor).
- **No tiene opciones predefinidas**: el valor lo ingresa el usuario. La tabla `customization_option` en este caso tiene una sola fila "virtual" con metadata de validación.
- Metadata del grupo: `{ "max_length": 20, "min_length": 1, "allowed_charset": "alphanumeric_spaces" }`.
- `price_modifier` vive en la opción única.

### `ENGRAVING_IMAGE`

- Render UI: uploader de imagen (PNG/SVG), con preview.
- Similar a `ENGRAVING_TEXT` (una "opción virtual" que permite upload).
- Metadata del grupo: `{ "max_size_mb": 5, "allowed_mime": ["image/png","image/svg+xml"], "recommended_dpi": 300 }`.
- El archivo subido se guarda en R2 y se referencia por URL firmada.

### `USER_FILE`

- Render UI: uploader de archivo 3D (STL/OBJ).
- Similar a los dos anteriores; opción virtual única.
- Metadata: `{ "max_size_mb": 100, "allowed_ext": ["stl","obj"] }`.
- Advertencia UI obligatoria: "Esta opción requiere revisión manual antes de imprimir. Te contactaremos." (hasta que exista cotización automática, v2+).
- El pedido que contiene un ítem con `USER_FILE` **no entra automáticamente en `queued`**: permanece en `paid` hasta que el admin revise y avance manualmente.

## Agregar un tipo nuevo en el futuro

Pasos para sumar (ej.) `FINISH` (acabado mate/brillante):

1. Agregar valor al enum `customization_type` en `apps/api/app/models/customization.py`.
2. Generar migración Alembic con `ALTER TYPE ... ADD VALUE 'FINISH'`.
3. Registrar validador en `apps/api/app/services/customization/validators.py` (un registro `TYPE → validator_fn`).
4. Registrar componente render en `apps/web/src/features/customization/registry.ts` (un registro `TYPE → React component`).
5. No se requiere cambiar la tabla de opciones ni el carrito: el JSONB de metadata absorbe las diferencias.

Si un tipo nuevo necesita un campo estructurado que no cabe en JSONB por razones de consulta, **esa es una señal para separar a una tabla propia**, no para romper el patrón genérico.

## Persistencia en el carrito y pedido

Cada item del carrito (`cart_item`) y del pedido (`order_item`) almacena las personalizaciones elegidas en una columna JSONB:

```json
{
  "selections": [
    { "group_id": 12, "option_ids": [45] },
    { "group_id": 13, "option_ids": [78] },
    { "group_id": 14, "value": "Juan", "option_id": 99 },
    { "group_id": 15, "file_id": "01HWXYZ..." }
  ],
  "resolved_modifier_cents": 250000,
  "snapshot_version": 3
}
```

- `option_ids` para tipos de selección (COLOR/MATERIAL/SIZE).
- `value` para tipos de texto.
- `file_id` para tipos con upload.
- `resolved_modifier_cents` es la suma de modifiers al momento de agregar al carrito; **se congela** en el pedido para no alterar el precio si el admin edita productos después.
- `snapshot_version` apunta a un snapshot inmutable del set de personalizaciones (opcional; mejora trazabilidad ante cambios).

## Validación server-side

Al agregar al carrito y al confirmar checkout, el backend valida para cada selección:
- El grupo existe y pertenece al producto.
- La opción existe y pertenece al grupo.
- Si el grupo es `required`, hay selección para él.
- Si `selection_mode == 'single'`, viene un solo `option_id`.
- Para `ENGRAVING_TEXT`: el `value` respeta `min_length`, `max_length`, `allowed_charset`.
- Para `ENGRAVING_IMAGE` / `USER_FILE`: el `file_id` existe, fue subido por el mismo usuario, respeta `max_size`, `mime_type` / `extension`.

Errores devueltos con código estable (ej. `CUSTOMIZATION_REQUIRED_GROUP_MISSING`, `CUSTOMIZATION_INVALID_OPTION`, `CUSTOMIZATION_FILE_TOO_LARGE`) y campo causante, para que el frontend pueda ubicar al usuario en el punto exacto.

## UX — reglas de render

- **Grupos con 1 opción**: se ocultan visualmente y se auto-seleccionan (no cargar al usuario con decisiones triviales).
- **Orden visible**: el admin define `sort_order` por grupo; default, alfabético.
- **Resumen de precio dinámico**: cada cambio de selección recalcula el subtotal sin round-trip al servidor, usando los modifiers ya cargados.
- **Opciones no disponibles**: si una opción está deshabilitada (p.ej. color agotado), se muestra tachada y con tooltip, no se oculta.
- **Reset**: un botón visible "Restaurar original" que vuelve a los defaults.
- **Accesibilidad**: cada swatch de color tiene aria-label con el nombre del color; nunca comunicar con color solamente.

## Precio con personalización

```
precio_unitario = base_price + sum(modifier de cada opción elegida)
subtotal_item  = precio_unitario * cantidad
subtotal_order = sum(subtotal_item)
```

Modifiers se almacenan siempre como **enteros en centavos**. Un modifier negativo (ej. descuento por no grabar) es válido, pero el precio_unitario nunca puede resultar < 0: el backend valida y rechaza la creación de tal producto con error claro al admin.
