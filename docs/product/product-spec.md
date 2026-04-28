# Product Spec — Aura

Especificación funcional del MVP de producción. Toda regla acá declarada es vinculante para backend, frontend y admin.

## Alcance del MVP

El MVP cubre:
- Catálogo navegable por categorías.
- Ficha de producto con preview 3D interactivo.
- Carrito y checkout para usuarios registrados.
- Personalización de productos (varios tipos, extensibles).
- Gestión de pedidos end-to-end (de `pending_payment` a `delivered`).
- Panel admin completo (productos, categorías, pedidos, usuarios, cupones, auditoría).
- Autenticación email+password, Google, Microsoft. JWT.
- Roles `user` y `admin` (solo un admin).

**Fuera de alcance** (explícito, v2.0+):
- Facturación electrónica AFIP.
- Cotización automática de archivos subidos por el usuario.
- Integración con Correo Argentino / OCA (pre-armado pero no activo).
- Multi-idioma (preparado, solo ES activo).
- Multi-admin y granularidad de permisos.
- Programa de fidelidad / puntos.

## Catálogo

### Categorías iniciales

El admin administra el CRUD, pero el sistema arranca con estas siete:

1. Decoración
2. Llaveros
3. Figuras
4. Utilitarios
5. Piezas técnicas
6. Regalos
7. Gaming

**Estructura**: jerarquía de 1 nivel en el MVP, pero el modelo de datos debe soportar subcategorías (campo `parent_id` nullable). UI inicial no expone subcategorías; el admin puede crearlas sin romper nada.

**Slug**: auto-generado desde el nombre (`kebab-case`, sin tildes). Editable por admin.

**Estado**: `active` / `archived`. Categoría archivada no aparece en listado público pero sus productos siguen accesibles por URL directa.

### Producto

Campos obligatorios:
- `name`, `slug`, `description` (rich text limitado: bold, italic, listas, links).
- `category_id`.
- `base_price` (ARS, almacenado en centavos como entero).
- `images` (mínimo 1, máximo 8; orden editable).
- `stock_mode`: `stocked` o `print_on_demand`.
- `status`: `draft`, `active`, `archived`.

Campos condicionales:
- Si `stock_mode == stocked`: `stock_quantity` (entero ≥ 0).
- Si `stock_mode == print_on_demand`: `lead_time_days` (entero ≥ 1).

Campos opcionales:
- `model_file_id` (FK a archivo 3D — ver `architecture/data-model.md`).
- `discount_id` (aplica descuento directo sin cupón).
- `customization_groups` (array, ver `product/customization-model.md`).
- `tags` (array de strings, para búsqueda y filtros futuros).
- `sku` (auto-generado si no se provee).
- `weight_grams`, `dimensions_mm` (para cálculo de envío futuro).

### Búsqueda y filtros

- **Búsqueda**: full-text sobre `name`, `description`, `tags`. Implementación: Postgres `tsvector` + `ts_rank`, español.
- **Filtros**:
  - Categoría (multi-select).
  - Precio (rango con slider).
  - Disponibilidad (`en stock`, `a pedido`).
  - Personalizable (sí/no).
- **Orden**: relevancia (default en búsqueda), más nuevos, precio asc/desc, más vendidos.
- **Paginación**: cursor-based, 24 productos por página.

## Personalización

Ver documento dedicado: `product/customization-model.md`. Resumen:
- Cada producto puede tener 0..N **grupos** de personalización.
- Cada grupo tiene 1..N **opciones**.
- Cada opción tiene un **modifier** de precio (positivo, cero o negativo) y un flag `required`.
- Tipos soportados en el MVP: `COLOR`, `MATERIAL`, `SIZE`, `ENGRAVING_TEXT`, `ENGRAVING_IMAGE`, `USER_FILE`.
- Diseñado para agregar nuevos tipos sin cambiar el schema de DB.

## Carrito

- El carrito **persiste en servidor** asociado al usuario (requiere login para operar).
- Un usuario tiene **un único carrito activo** (`status = open`). Al confirmar compra se convierte en `converted` y se crea uno nuevo vacío cuando vuelva a agregar.
- **Items duplicados con mismas personalizaciones se agrupan** (suman cantidad). Items con personalizaciones distintas son ítems separados.
- Cantidad: entero ≥ 1. Máximo por producto: 20 unidades (configurable).
- **Validación de stock** al agregar y al checkout. Si un producto `stocked` pasa a stock 0, el ítem se marca como no-disponible; el usuario debe removerlo para avanzar.
- **Validación de precios** al checkout: si `base_price` o `modifier` cambió desde que se agregó, se muestra banner de advertencia con diferencia y se recalcula. Nunca cobrar un precio distinto al mostrado.

## Checkout

Flujo lineal en 3 pasos, con back libre:

1. **Envío**: dirección de envío (del perfil o nueva). Método: por ahora solo "retiro" o "envío estándar self-service". El cálculo de costo de envío es **fijo configurable por admin** hasta v2.0.
2. **Pago**: selección de pasarela (MercadoPago, Stripe, PayPal). Redirección al checkout externo. Webhook de confirmación activa el pedido.
3. **Confirmación**: pantalla de éxito con número de pedido, resumen, email de confirmación enviado automáticamente.

### Reglas de pago

- MercadoPago es el **default sugerido** en UI (mayor adopción en Argentina).
- Todos los pagos se crean con idempotency key por `order.id`. Un usuario que cierra la pestaña y vuelve a "pagar" sobre el mismo pedido no genera doble pago.
- Webhooks firmados; rechazar cualquier petición sin firma válida.
- Un pedido queda `pending_payment` hasta recibir webhook de confirmación. Si el webhook no llega en 60 minutos, queue job revisa estado vía API de la pasarela.

## Pedidos

### Máquina de estados

```
pending_payment → paid → queued → printing → shipped → delivered
                     ↓
                 cancelled (por usuario antes de queued, por admin en cualquier momento antes de shipped)
                     ↓
                 refunded (total o parcial, solo admin)
```

Reglas:
- El usuario **puede cancelar** mientras el pedido esté en `pending_payment` o `paid` (antes de `queued`).
- **Solo admin** puede mover a `queued`, `printing`, `shipped`, `delivered`, `refunded`.
- Cada cambio de estado genera un registro en `order_status_history` con autor, timestamp y nota opcional.
- Email al usuario en: `paid`, `printing`, `shipped`, `delivered`, `cancelled`, `refunded`.

### Estado visible al usuario

| Estado interno | Etiqueta UI |
|---|---|
| `pending_payment` | Esperando pago |
| `paid` | Pago confirmado |
| `queued` | En cola |
| `printing` | Imprimiéndose |
| `shipped` | En camino |
| `delivered` | Entregado |
| `cancelled` | Cancelado |
| `refunded` | Reembolsado |

## Usuario

### Registro

- Email + password, o OAuth Google, o OAuth Microsoft.
- Password: mínimo 10 caracteres, debe tener letra y número. Hash con **argon2id**.
- **Verificación de email obligatoria**: hasta no verificar, el usuario puede navegar catálogo pero **no puede checkout**. Link de verificación expira en 24h.
- OAuth: si el email del provider ya existe como cuenta local, se vincula tras pedir password local; nunca se toma el control silencioso.

### Recuperación de password

- Solicitar reset envía email con token (JWT corto, 30 min, un solo uso).
- El reset **no revela** si el email existe: mensaje siempre es "si el email existe, recibirás un link".

### Perfil

Acceso desde `/mi-cuenta`:
- **Datos personales**: nombre, apellido, DNI (opcional, para envío), teléfono.
- **Direcciones**: CRUD de direcciones guardadas (máximo 5). Una marcada como default.
- **Historial de pedidos**: listado paginado con estado, fecha, total, link a detalle.
- **Detalle de pedido**: productos, personalizaciones aplicadas, dirección, pagos, timeline de estados.
- **Lista de deseos (wishlist)**: productos guardados. Acceso rápido a "agregar al carrito" desde ahí.

## Admin / CRM

Acceso en `/admin` (frontend separado-por-ruta, mismo proyecto `apps/web`). Solo usuarios con `role = admin` acceden; el resto recibe 404 (no 403, para no filtrar existencia).

### Funciones requeridas

- **Dashboard**: KPIs del período (pedidos, ingresos, items vendidos top 10, tasa de conversión aproximada). Filtros por rango de fecha.
- **Productos**: CRUD completo. Editor de personalizaciones. Drag-and-drop de imágenes. Subida de STL/GLB. Preview 3D en el editor igual al público.
- **Categorías**: CRUD. Reordenar.
- **Pedidos**: listado filtrable (estado, fecha, usuario, total). Detalle con acciones: avanzar estado, cancelar, reembolsar (total/parcial), agregar nota interna, imprimir orden de producción (PDF simple).
- **Usuarios**: listado, detalle (datos + pedidos). Acción: suspender cuenta (no eliminar, preserva histórico).
- **Cupones**: CRUD de códigos y de descuentos automáticos. Ver sección "Descuentos".
- **Auditoría**: timeline de acciones del admin sobre entidades sensibles (productos, pedidos, usuarios, cupones). Filtros por entidad, fecha, tipo de acción.
- **Configuración**: nombre del sitio, email de contacto, costo fijo de envío, textos legales (términos, privacidad, FAQ).

## Descuentos

Tres mecanismos, convivientes:

1. **Cupones por código**: admin crea código (ej. `VERANO20`), tipo (`percentage` | `fixed`), valor, validez (rango de fechas), usos máximos totales, usos por usuario, monto mínimo de carrito, categorías/productos aplicables (opcional).
2. **Descuentos automáticos por producto o categoría**: admin marca "-15% en Decoración" sin necesidad de cupón. Se aplica al mostrar precio.
3. **Descuentos por volumen**: admin configura reglas tipo "10% si compras 3+ del mismo producto".

**Reglas de aplicación**:
- Solo un cupón activo por pedido.
- Descuentos automáticos siempre se aplican (no requieren código).
- Cupón **puede** combinarse con descuento automático si el admin lo marca como combinable (flag `stacks_with_automatic`).
- El descuento se calcula sobre el **subtotal tras aplicar modifiers de personalización**.

## Reglas generales de negocio

- **Moneda única**: ARS. Todos los precios se almacenan como enteros (centavos) para evitar floats.
- **Redondeo**: al medio peso más cercano al mostrar, pero almacenar valor exacto.
- **Zonas horarias**: admin y usuarios ven todo en `America/Argentina/Buenos_Aires`. DB en UTC.
- **Idempotencia**: toda operación de escritura que pueda reintentarse acepta `Idempotency-Key` header en el backend y persiste la primera respuesta 24h.
- **Rate limiting**: ver `architecture/security.md`.
- **Borrado**: **soft-delete** en entidades con referencias (usuarios, productos, categorías, pedidos). Hard-delete solo en entidades sin histórico (carritos abandonados tras 90 días, tokens expirados).

## Email transaccional

Proveedor: **Resend**. Plantillas en MJML, renderizadas server-side.

Emails del MVP:
- Verificación de email (registro).
- Reset de password.
- Pedido recibido (al pasar a `paid`).
- Pedido en impresión (`printing`).
- Pedido enviado (`shipped`) con nota para número de seguimiento cuando exista.
- Pedido entregado (`delivered`).
- Pedido cancelado.
- Pedido reembolsado.

Cada email incluye logo, color de marca, número de pedido, link a la orden y link de baja solo para emails **no-transaccionales** (el MVP no tiene marketing aún).
