# API Contract — p3rDiz

Contrato REST público del backend. Base URL: `/api/v1`. La especificación OpenAPI real se autogenera desde FastAPI; este documento es la **referencia humana** que obliga al nombre, forma y comportamiento de los endpoints.

## Convenciones

- **Base URL**: `https://api.perdiz.ar/v1` en prod; `http://localhost:8000/v1` en dev.
- **Autenticación**: `Authorization: Bearer <access_token>` excepto donde se indique lo contrario.
- **Content-Type**: `application/json` en requests y responses. Excepciones documentadas explícitamente.
- **Idempotencia**: endpoints de mutación aceptan `Idempotency-Key` (opcional). Primera respuesta se cachea 24h para la misma key.
- **Paginación**: cursor-based. Parámetros `?cursor=<opaque>&limit=<int>` (limit máx 100, default 24).
- **Ordenamiento**: `?sort=<field>&order=<asc|desc>`.
- **Filtros**: query params documentados por endpoint.
- **Respuestas de error**: formato definido en `backend/conventions.md`.
- **Fechas**: ISO 8601 UTC (`2026-04-22T14:33:00Z`).
- **IDs**: ULID en strings de 26 chars.

## Auth

### `POST /auth/register`
Pública. Crea cuenta nueva. Dispara envío de email de verificación.
```json
// request
{ "email": "juan@ejemplo.com", "password": "unaPassword123", "first_name": "Juan", "last_name": "Pérez" }

// 201
{ "user": { "id": "01HW...", "email": "juan@ejemplo.com", "email_verified": false } }
```
Errores: `AUTH_EMAIL_ALREADY_EXISTS`, `VALIDATION_*`.

### `POST /auth/login`
Pública. Retorna access + setea cookie refresh.
```json
// request
{ "email": "juan@ejemplo.com", "password": "..." }

// 200
{ "access_token": "eyJ...", "user": { ... } }
// + Set-Cookie: refresh_token=...; HttpOnly; Secure; SameSite=Lax; Path=/auth/refresh
```
Errores: `AUTH_INVALID_CREDENTIALS`, `AUTH_ACCOUNT_LOCKED`, `AUTH_ACCOUNT_SUSPENDED`.

### `POST /auth/refresh`
Lee cookie. Retorna nuevo access + rota cookie.
```json
// 200
{ "access_token": "eyJ..." }
```
Errores: `AUTH_REFRESH_INVALID`, `AUTH_REFRESH_EXPIRED`, `AUTH_REFRESH_REUSED` (revoca familia).

### `POST /auth/logout`
Requiere access. Revoca familia del refresh actual.
Respuesta 204.

### `POST /auth/email/verify`
Pública. Consume token de verificación.
```json
// request
{ "token": "..." }
// 200
{ "user": { "id": "...", "email_verified": true } }
```

### `POST /auth/email/resend-verification`
Requiere access. Reenvía email de verificación.
Respuesta 204.

### `POST /auth/password/forgot`
Pública. Siempre 200 aunque el email no exista.
```json
// request
{ "email": "juan@ejemplo.com" }
// 200
{ "message": "Si el email existe, te enviamos un link." }
```

### `POST /auth/password/reset`
Pública. Consume token y resetea password.
```json
// request
{ "token": "...", "password": "nuevaPassword123" }
// 200
{ "message": "Password actualizado." }
```

### `GET /auth/oauth/{provider}/authorize`
Pública. `provider ∈ {google, microsoft}`. Redirige al provider con state + PKCE.

### `GET /auth/oauth/{provider}/callback`
Pública. El provider redirige acá. El backend completa el flujo y redirige al frontend con cookie seteada y access en query param **temporal** que el frontend consume y descarta (o mejor, devuelve HTML que postMessage al opener).

## Usuario

### `GET /users/me`
Requiere access.
```json
// 200
{ "id": "...", "email": "...", "email_verified": true, "role": "user",
  "first_name": "Juan", "last_name": "Pérez", "phone": "+54...", "dni": null }
```

### `PATCH /users/me`
Requiere access. Actualiza campos del perfil. No permite cambiar `email`, `role`, `status`.

### `POST /users/me/email/change`
Requiere access + verified. Dispara email de confirmación al nuevo email; el cambio se aplica al verificar.

### `GET /users/me/addresses` · `POST /users/me/addresses` · `PATCH /users/me/addresses/{id}` · `DELETE /users/me/addresses/{id}`
CRUD de direcciones propias. Máximo 5.

### `GET /users/me/sessions` · `DELETE /users/me/sessions/{family_id}`
Lista y revoca sesiones (familias de refresh).

## Catálogo

### `GET /categories`
Pública. Retorna árbol de categorías `active`. Filtros: `?include_archived=true` (solo admin, ignorado si no).

### `GET /categories/{slug}`
Pública. Detalle + productos (opcional `?with_products=true`, limitado).

### `GET /products`
Pública. Listado.
Query params: `q`, `category=<slug|id>` (multi), `price_min`, `price_max`, `availability=in_stock|on_demand`, `customizable=true|false`, `sort=relevance|newest|price_asc|price_desc|popularity`, `cursor`, `limit`.
```json
// 200
{
  "data": [
    {
      "id": "01HW...",
      "name": "Llavero low-poly perdiz",
      "slug": "llavero-low-poly-perdiz",
      "price_cents": 150000,
      "currency": "ARS",
      "discounted_price_cents": 127500,
      "images": [{ "url": "...", "alt": "..." }],
      "category": { "id": "...", "name": "Llaveros", "slug": "llaveros" },
      "availability": "in_stock",
      "customizable": true,
      "badges": ["nuevo", "oferta"]
    }
  ],
  "pagination": { "cursor": "...", "next_cursor": "...", "has_more": true, "count": 24 }
}
```

### `GET /products/{slug}`
Pública. Detalle completo, incluye `customization_groups`, imágenes, modelo 3D (GLB url).

```json
{
  "id": "...",
  "name": "...",
  "slug": "...",
  "description_html": "<p>...</p>",
  "price_cents": 150000,
  "discounted_price_cents": null,
  "currency": "ARS",
  "category": { "id": "...", "name": "...", "slug": "..." },
  "images": [...],
  "model_glb_url": "https://r2.../model.glb",
  "stock_mode": "stocked",
  "stock_quantity": 12,
  "lead_time_days": null,
  "customization_groups": [
    {
      "id": "...",
      "name": "Color",
      "type": "COLOR",
      "required": true,
      "selection_mode": "single",
      "options": [
        { "id": "...", "label": "Rojo", "price_modifier_cents": 0, "metadata": { "hex": "#FF0000" }, "is_available": true, "is_default": true }
      ]
    }
  ],
  "tags": ["perdiz", "regalo"]
}
```

## Wishlist

### `GET /wishlist` · `POST /wishlist` · `DELETE /wishlist/{product_id}`
Requiere access. Modelo simple.

## Carrito

### `GET /cart`
Requiere access. Retorna carrito abierto (auto-creado si no existe). Incluye items con precios actuales y avisos de cambios.

```json
{
  "id": "...",
  "items": [
    {
      "id": "...",
      "product_id": "...",
      "name_snapshot": "...",
      "image_url": "...",
      "quantity": 2,
      "unit_price_cents": 150000,
      "modifiers_total_cents": 5000,
      "line_total_cents": 310000,
      "customizations": { "selections": [...], "resolved_modifier_cents": 5000 },
      "warnings": []
    }
  ],
  "subtotal_cents": 310000,
  "automatic_discounts_cents": 31000,
  "coupon": null,
  "coupon_discount_cents": 0,
  "shipping_cents": 0,
  "total_cents": 279000
}
```

### `POST /cart/items`
Agregar ítem.
```json
{ "product_id": "...", "quantity": 1, "customizations": { "selections": [...] } }
```

### `PATCH /cart/items/{item_id}`
Actualizar cantidad o personalización.

### `DELETE /cart/items/{item_id}`
Remover ítem.

### `POST /cart/coupon`
Aplicar cupón por código.
```json
{ "code": "VERANO20" }
```
Errores: `COUPON_NOT_FOUND`, `COUPON_EXPIRED`, `COUPON_MIN_ORDER_NOT_MET`, `COUPON_MAX_USES_REACHED`.

### `DELETE /cart/coupon`
Quitar cupón.

## Checkout y pedidos

### `POST /checkout`
Requiere access + verified. Crea pedido en estado `pending_payment`, inicia pago con la pasarela elegida, devuelve URL de redirección.
```json
// request
{
  "shipping_address_id": "...",
  "shipping_method": "standard",  // o "pickup"
  "payment_provider": "mercadopago"  // o "stripe" o "paypal"
}
// 201
{
  "order": { "id": "...", "status": "pending_payment", "total_cents": 279000, ... },
  "payment_redirect_url": "https://www.mercadopago.com/..."
}
```

### `GET /orders`
Requiere access. Lista pedidos del usuario actual.

### `GET /orders/{id}`
Requiere access. Detalle con timeline.

### `POST /orders/{id}/cancel`
Requiere access. Cancela si está en `pending_payment` o `paid`.

## Uploads

### `POST /uploads/presign`
Requiere access (para imágenes de personalización y user files).
```json
// request
{ "kind": "user_upload_image", "mime_type": "image/png", "size_bytes": 1234567, "filename": "logo.png" }
// 200
{
  "upload_url": "https://...r2...signed",
  "method": "PUT",
  "headers": { "Content-Type": "image/png" },
  "storage_key": "uploads/01HW.../logo.png",
  "expires_at": "2026-04-22T14:43:00Z"
}
```

### `POST /uploads/commit`
Requiere access. Confirma que el archivo terminó de subir; valida magic bytes y crea `media_files`.
```json
// request
{ "storage_key": "...", "kind": "user_upload_image" }
// 200
{ "media_file_id": "...", "url": "..." }
```

## Webhooks

### `POST /webhooks/mercadopago`
Pública. Valida firma MP. Procesa notificación.

### `POST /webhooks/stripe`
Pública. Valida firma Stripe.

### `POST /webhooks/paypal`
Pública. Valida firma PayPal.

Todos responden 200 si procesan correctamente o si es duplicado (idempotencia). 400 si firma inválida.

## Admin — productos

Todos requieren `require_role('admin')`. Responden 404 a no-admins.

### `GET /admin/products`
Listado con filtros amplios: incluye `draft`, `archived`. Paginado.

### `POST /admin/products`
Crea producto (status `draft` por default).

### `GET /admin/products/{id}`
Detalle admin.

### `PATCH /admin/products/{id}`
Actualiza campos.

### `DELETE /admin/products/{id}`
Soft-delete (marca `deleted_at`).

### `POST /admin/products/{id}/customization-groups` · `PATCH .../{group_id}` · `DELETE .../{group_id}`
CRUD de grupos de personalización.

### `POST /admin/products/{id}/customization-groups/{group_id}/options` · `PATCH .../{option_id}` · `DELETE .../{option_id}`
CRUD de opciones.

### `POST /admin/products/{id}/images` · `PATCH .../{image_id}` · `DELETE .../{image_id}`
Gestionar imágenes (orden, alt, reemplazo).

### `POST /admin/uploads/presign` · `POST /admin/uploads/commit`
Versión admin de upload (acepta `model_stl`, `model_glb` kinds).

## Admin — categorías

### `GET /admin/categories` · `POST /admin/categories` · `PATCH /admin/categories/{id}` · `DELETE /admin/categories/{id}`

## Admin — pedidos

### `GET /admin/orders`
Filtros: `status`, `user_id`, `from`, `to`, `q` (búsqueda por nombre de usuario, id).

### `GET /admin/orders/{id}`

### `POST /admin/orders/{id}/transition`
Cambia estado.
```json
{ "to_status": "queued", "note": "..." }
```
Valida transiciones permitidas según máquina de estados en `product-spec.md`.

### `POST /admin/orders/{id}/refund`
```json
{ "amount_cents": 279000, "reason": "..." }
```

### `GET /admin/orders/{id}/production-sheet`
Retorna PDF con hoja de producción (items, archivos STL descargables).

## Admin — usuarios

### `GET /admin/users`
### `GET /admin/users/{id}`
### `POST /admin/users/{id}/suspend` · `POST /admin/users/{id}/unsuspend`

## Admin — cupones y descuentos

### `GET /admin/coupons` · `POST /admin/coupons` · `PATCH /admin/coupons/{id}` · `DELETE /admin/coupons/{id}`
### `GET /admin/discounts` · `POST /admin/discounts` · `PATCH /admin/discounts/{id}` · `DELETE /admin/discounts/{id}`
(descuentos automáticos por categoría/producto)
### `GET /admin/products/{id}/volume-discounts` · `POST ...` · `DELETE .../{vd_id}`

## Admin — settings

### `GET /admin/settings`
### `PATCH /admin/settings`
Recibe `{ key: value }` objects.

## Admin — auditoría

### `GET /admin/audit-log`
Filtros: `entity_type`, `entity_id`, `actor_id`, `action`, `from`, `to`. Paginado.

## Admin — dashboard

### `GET /admin/dashboard/kpis`
Query: `?from=...&to=...`.
```json
{
  "orders_count": 142,
  "revenue_cents": 35400000,
  "items_sold": 210,
  "top_products": [...],
  "orders_by_status": { "paid": 20, "printing": 14, ... },
  "new_users": 33
}
```

## Health y observabilidad

### `GET /health`
Pública. Retorna 200 simple: `{ "status": "ok" }`.

### `GET /health/deep`
Chequea DB, Redis, R2. Retorna 200/503 con detalle por dependencia.

## Versionado del API

- Todo vive bajo `/v1`. Cambios breaking abren `/v2`; el viejo soporta deprecación 3 meses mínimo.
- Cambios aditivos (nuevo campo opcional, nuevo endpoint) **no** abren nueva versión.
- La spec OpenAPI se versiona en `packages/api-client/openapi.json` y se regenera en CI.
