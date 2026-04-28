# Modelo de datos — Aura

Modelo relacional de PostgreSQL 16. Los nombres acá escritos son **vinculantes** para los modelos SQLAlchemy y las migraciones Alembic.

## Convenciones generales

- Tablas en **snake_case plural** (`users`, `order_items`).
- PK: `id` **ULID** (`CHAR(26)`) generado en aplicación, ordenable por tiempo. Alternativa de fallback: `BIGSERIAL` si un proyecto interno bloquea ULIDs; el MVP usa ULID.
- Timestamps UTC: todas las tablas con actividad temporal tienen `created_at` y `updated_at` (`TIMESTAMPTZ`, default `now()`).
- Soft-delete: columna `deleted_at TIMESTAMPTZ NULL` donde corresponda. Queries por default filtran `deleted_at IS NULL` via `event.listen` de SQLAlchemy.
- Dinero: **entero en centavos ARS**, nombre de columna con sufijo `_cents` (ej. `base_price_cents`).
- Enums: **Postgres enum types** para estados conocidos. Extensión con `ALTER TYPE ... ADD VALUE`.
- FKs: `ON DELETE RESTRICT` por default. `CASCADE` solo en tablas puente y en sub-entidades claramente dependientes (ej. `order_items`, `cart_items`).
- Índices: todo FK indexado, todo campo de filtro frecuente indexado, `slug` único por tabla pública.

## Entidades

### `users`

```
id                 CHAR(26) PK
email              CITEXT UNIQUE NOT NULL
email_verified_at  TIMESTAMPTZ NULL
password_hash      TEXT NULL          -- null si solo se autentica por OAuth
role               user_role NOT NULL DEFAULT 'user'  -- enum: 'user', 'admin'
status             user_status NOT NULL DEFAULT 'active'  -- 'active','suspended'
first_name         TEXT NULL
last_name          TEXT NULL
phone              TEXT NULL
dni                TEXT NULL
created_at         TIMESTAMPTZ DEFAULT now()
updated_at         TIMESTAMPTZ DEFAULT now()
deleted_at         TIMESTAMPTZ NULL
```

Índices: `(email)` (único implícito), `(role)`, `(status)`.

### `social_accounts`

```
id            CHAR(26) PK
user_id       CHAR(26) FK users.id ON DELETE CASCADE
provider      oauth_provider NOT NULL   -- enum: 'google','microsoft'
provider_sub  TEXT NOT NULL             -- id estable del provider
email_at_link TEXT NOT NULL             -- email informado por el provider al vincular
created_at    TIMESTAMPTZ DEFAULT now()
UNIQUE (provider, provider_sub)
```

### `addresses`

```
id           CHAR(26) PK
user_id      CHAR(26) FK users.id ON DELETE CASCADE
label        TEXT NOT NULL             -- "Casa", "Oficina"
recipient    TEXT NOT NULL
phone        TEXT NULL
street       TEXT NOT NULL
number       TEXT NULL
apartment    TEXT NULL
city         TEXT NOT NULL
province     TEXT NOT NULL             -- Buenos Aires, Córdoba, etc.
postal_code  TEXT NOT NULL
notes        TEXT NULL
is_default   BOOLEAN NOT NULL DEFAULT false
created_at   TIMESTAMPTZ DEFAULT now()
updated_at   TIMESTAMPTZ DEFAULT now()
```

Un usuario puede tener máximo 5 direcciones (validación de app, no DB). Solo una con `is_default = true` por usuario (índice parcial único).

### `categories`

```
id           CHAR(26) PK
name         TEXT NOT NULL
slug         TEXT NOT NULL UNIQUE
parent_id    CHAR(26) NULL FK categories.id ON DELETE RESTRICT
description  TEXT NULL
image_url    TEXT NULL
sort_order   INT NOT NULL DEFAULT 0
status       category_status NOT NULL DEFAULT 'active'  -- 'active','archived'
created_at   TIMESTAMPTZ DEFAULT now()
updated_at   TIMESTAMPTZ DEFAULT now()
deleted_at   TIMESTAMPTZ NULL
```

### `products`

```
id                CHAR(26) PK
category_id       CHAR(26) FK categories.id ON DELETE RESTRICT
name              TEXT NOT NULL
slug              TEXT NOT NULL UNIQUE
description       TEXT NULL                -- rich text HTML sanitizado
base_price_cents  INT NOT NULL CHECK (base_price_cents >= 0)
stock_mode        stock_mode NOT NULL      -- 'stocked','print_on_demand'
stock_quantity    INT NULL CHECK (stock_quantity IS NULL OR stock_quantity >= 0)
lead_time_days    INT NULL CHECK (lead_time_days IS NULL OR lead_time_days >= 1)
weight_grams      INT NULL
dimensions_mm     INT[] NULL               -- [x, y, z]
sku               TEXT UNIQUE NOT NULL
tags              TEXT[] DEFAULT '{}'
status            product_status NOT NULL DEFAULT 'draft'  -- 'draft','active','archived'
search_tsv        TSVECTOR                 -- GENERATED ALWAYS AS STORED, spanish dict, weights name>description. Tags quedan fuera del tsvector (polimorfismo array_to_string no es immutable en Postgres para columnas generadas STORED) — se indexan aparte con GIN y se buscan vía `tags @> ARRAY[...]`.
model_file_id     CHAR(26) NULL FK media_files.id ON DELETE SET NULL
created_at        TIMESTAMPTZ DEFAULT now()
updated_at        TIMESTAMPTZ DEFAULT now()
deleted_at        TIMESTAMPTZ NULL

CHECK (
  (stock_mode='stocked' AND stock_quantity IS NOT NULL AND lead_time_days IS NULL)
  OR
  (stock_mode='print_on_demand' AND lead_time_days IS NOT NULL AND stock_quantity IS NULL)
)
```

Índices: `category_id`, `status`, `tags` (GIN), `search_tsv` (GIN), `slug`.

### `product_images`

```
id           CHAR(26) PK
product_id   CHAR(26) FK products.id ON DELETE CASCADE
media_file_id CHAR(26) FK media_files.id ON DELETE RESTRICT
alt_text     TEXT NULL
sort_order   INT NOT NULL DEFAULT 0
```

### `media_files`

Tabla única para **todos** los archivos almacenados en R2 (imágenes, STL, GLB, uploads de usuario).

```
id             CHAR(26) PK
owner_user_id  CHAR(26) NULL FK users.id ON DELETE SET NULL  -- null si sube un admin
kind           media_kind NOT NULL  -- 'image','model_stl','model_glb','user_upload_image','user_upload_model'
mime_type      TEXT NOT NULL
size_bytes     BIGINT NOT NULL
storage_key    TEXT NOT NULL UNIQUE        -- key en R2
public_url     TEXT NULL                   -- null si requiere URL firmada
checksum_sha256 TEXT NULL
metadata       JSONB DEFAULT '{}'::jsonb   -- width/height para imágenes, triangles para STL, etc.
created_at     TIMESTAMPTZ DEFAULT now()
deleted_at     TIMESTAMPTZ NULL
```

Relación con producto: un `product.model_file_id` apunta al STL fuente (kind `model_stl`). El GLB derivado se asocia vía una columna adicional `derived_from_id` (self-FK a `media_files.id`) cuando se genera la versión liviana:

```
derived_from_id CHAR(26) NULL FK media_files.id
```

### `customization_groups`

```
id             CHAR(26) PK
product_id     CHAR(26) FK products.id ON DELETE CASCADE
name           TEXT NOT NULL            -- "Color"
type           customization_type NOT NULL  -- enum extensible
required       BOOLEAN NOT NULL DEFAULT false
selection_mode customization_selection NOT NULL  -- 'single','multiple'
sort_order     INT NOT NULL DEFAULT 0
metadata       JSONB DEFAULT '{}'::jsonb  -- per-type: max_length, max_size_mb, etc.
created_at     TIMESTAMPTZ DEFAULT now()
updated_at     TIMESTAMPTZ DEFAULT now()
```

### `customization_options`

```
id                    CHAR(26) PK
group_id              CHAR(26) FK customization_groups.id ON DELETE CASCADE
label                 TEXT NOT NULL
price_modifier_cents  INT NOT NULL DEFAULT 0
is_default            BOOLEAN NOT NULL DEFAULT false
is_available          BOOLEAN NOT NULL DEFAULT true
sort_order            INT NOT NULL DEFAULT 0
metadata              JSONB DEFAULT '{}'::jsonb   -- hex, dimensions, etc.
created_at            TIMESTAMPTZ DEFAULT now()
updated_at            TIMESTAMPTZ DEFAULT now()
```

Para tipos sin opciones predefinidas (ENGRAVING_TEXT, ENGRAVING_IMAGE, USER_FILE), se crea una única opción "virtual" con `label = 'user_input'` que sostiene el `price_modifier_cents`.

### `carts`

```
id          CHAR(26) PK
user_id     CHAR(26) FK users.id ON DELETE CASCADE
status      cart_status NOT NULL DEFAULT 'open'  -- 'open','converted','abandoned'
created_at  TIMESTAMPTZ DEFAULT now()
updated_at  TIMESTAMPTZ DEFAULT now()
```

Un usuario tiene a lo sumo un cart en estado `open` (índice parcial único en `user_id` donde `status='open'`).

### `cart_items`

```
id                       CHAR(26) PK
cart_id                  CHAR(26) FK carts.id ON DELETE CASCADE
product_id               CHAR(26) FK products.id ON DELETE RESTRICT
quantity                 INT NOT NULL CHECK (quantity BETWEEN 1 AND 20)
unit_price_cents         INT NOT NULL            -- snapshot al agregar
modifiers_total_cents    INT NOT NULL DEFAULT 0
customizations           JSONB NOT NULL DEFAULT '[]'::jsonb
added_at                 TIMESTAMPTZ DEFAULT now()
updated_at               TIMESTAMPTZ DEFAULT now()
```

Estructura de `customizations` definida en `product/customization-model.md`.

### `orders`

```
id                     CHAR(26) PK
user_id                CHAR(26) FK users.id ON DELETE RESTRICT
status                 order_status NOT NULL DEFAULT 'pending_payment'
   -- 'pending_payment','paid','queued','printing','shipped','delivered','cancelled','refunded'
subtotal_cents         INT NOT NULL
discount_cents         INT NOT NULL DEFAULT 0
shipping_cents         INT NOT NULL DEFAULT 0
total_cents            INT NOT NULL
currency               CHAR(3) NOT NULL DEFAULT 'ARS'
coupon_id              CHAR(26) NULL FK coupons.id ON DELETE SET NULL
shipping_address_json  JSONB NOT NULL          -- snapshot inmutable de la dirección al momento del pedido
shipping_method        TEXT NOT NULL           -- 'pickup','standard'
admin_notes            TEXT NULL
placed_at              TIMESTAMPTZ DEFAULT now()
paid_at                TIMESTAMPTZ NULL
shipped_at             TIMESTAMPTZ NULL
delivered_at           TIMESTAMPTZ NULL
cancelled_at           TIMESTAMPTZ NULL
refunded_at            TIMESTAMPTZ NULL
created_at             TIMESTAMPTZ DEFAULT now()
updated_at             TIMESTAMPTZ DEFAULT now()
```

### `order_items`

```
id                       CHAR(26) PK
order_id                 CHAR(26) FK orders.id ON DELETE CASCADE
product_id               CHAR(26) FK products.id ON DELETE RESTRICT
product_name_snapshot    TEXT NOT NULL     -- para preservar aunque el admin cambie el nombre
quantity                 INT NOT NULL
unit_price_cents         INT NOT NULL
modifiers_total_cents    INT NOT NULL DEFAULT 0
line_total_cents         INT NOT NULL
customizations           JSONB NOT NULL DEFAULT '[]'::jsonb
```

### `order_status_history`

```
id           CHAR(26) PK
order_id     CHAR(26) FK orders.id ON DELETE CASCADE
from_status  order_status NULL
to_status    order_status NOT NULL
changed_by   CHAR(26) NULL FK users.id ON DELETE SET NULL
note         TEXT NULL
changed_at   TIMESTAMPTZ DEFAULT now()
```

### `payments`

```
id                   CHAR(26) PK
order_id             CHAR(26) FK orders.id ON DELETE RESTRICT
provider             payment_provider NOT NULL  -- 'mercadopago','stripe','paypal'
provider_payment_id  TEXT NOT NULL
status               payment_status NOT NULL    -- 'pending','approved','rejected','refunded'
amount_cents         INT NOT NULL
currency             CHAR(3) NOT NULL DEFAULT 'ARS'
raw_webhook_events   JSONB NOT NULL DEFAULT '[]'::jsonb
created_at           TIMESTAMPTZ DEFAULT now()
updated_at           TIMESTAMPTZ DEFAULT now()
UNIQUE (provider, provider_payment_id)
```

### `coupons`

```
id                        CHAR(26) PK
code                      TEXT UNIQUE NOT NULL        -- CI comparado insensible (lowercase en DB)
type                      discount_type NOT NULL      -- 'percentage','fixed' (enum compartido con volume_discounts + automatic_discounts)
value                     INT NOT NULL                -- si percentage: 1..100; si fixed: centavos
min_order_cents           INT NOT NULL DEFAULT 0
valid_from                TIMESTAMPTZ NULL
valid_until               TIMESTAMPTZ NULL
max_uses_total            INT NULL
max_uses_per_user         INT NULL
applicable_category_ids   CHAR(26)[] DEFAULT '{}'
applicable_product_ids    CHAR(26)[] DEFAULT '{}'
stacks_with_automatic     BOOLEAN NOT NULL DEFAULT false
status                    coupon_status NOT NULL DEFAULT 'active'  -- 'active','disabled'
created_at                TIMESTAMPTZ DEFAULT now()
updated_at                TIMESTAMPTZ DEFAULT now()
```

### `coupon_redemptions`

```
id          CHAR(26) PK
coupon_id   CHAR(26) FK coupons.id ON DELETE RESTRICT
order_id    CHAR(26) FK orders.id ON DELETE CASCADE
user_id     CHAR(26) FK users.id ON DELETE SET NULL
redeemed_at TIMESTAMPTZ DEFAULT now()
```

### `automatic_discounts`

```
id              CHAR(26) PK
name            TEXT NOT NULL
type            discount_type NOT NULL     -- enum compartido (ver coupons)
value           INT NOT NULL
scope           discount_scope NOT NULL    -- 'category','product'
target_id       CHAR(26) NOT NULL          -- category_id o product_id
valid_from      TIMESTAMPTZ NULL
valid_until     TIMESTAMPTZ NULL
status          discount_status NOT NULL DEFAULT 'active'
created_at      TIMESTAMPTZ DEFAULT now()
updated_at      TIMESTAMPTZ DEFAULT now()
```

### `volume_discounts`

```
id              CHAR(26) PK
product_id      CHAR(26) FK products.id ON DELETE CASCADE
min_quantity    INT NOT NULL CHECK (min_quantity >= 2)
type            discount_type NOT NULL      -- enum compartido (ver coupons)
value           INT NOT NULL CHECK (value > 0)
created_at      TIMESTAMPTZ DEFAULT now()
```

### `wishlist_items`

```
id          CHAR(26) PK
user_id     CHAR(26) FK users.id ON DELETE CASCADE
product_id  CHAR(26) FK products.id ON DELETE CASCADE
created_at  TIMESTAMPTZ DEFAULT now()
UNIQUE (user_id, product_id)
```

### `refresh_tokens`

```
id           CHAR(26) PK
user_id      CHAR(26) FK users.id ON DELETE CASCADE
token_hash   TEXT NOT NULL              -- SHA-256 del token; nunca se guarda plaintext
family_id    CHAR(26) NOT NULL          -- agrupa una cadena rotativa
parent_id    CHAR(26) NULL FK refresh_tokens.id
issued_at    TIMESTAMPTZ DEFAULT now()
expires_at   TIMESTAMPTZ NOT NULL
revoked_at   TIMESTAMPTZ NULL
user_agent   TEXT NULL
ip           INET NULL
```

Ver `architecture/security.md` para la política de rotación y detección de reuso.

### `email_verification_tokens` / `password_reset_tokens`

```
id          CHAR(26) PK
user_id     CHAR(26) FK users.id ON DELETE CASCADE
token_hash  TEXT NOT NULL UNIQUE
expires_at  TIMESTAMPTZ NOT NULL
used_at     TIMESTAMPTZ NULL
created_at  TIMESTAMPTZ DEFAULT now()
```

Una tabla por tipo (evita confusión de propósito).

### `audit_log`

```
id            CHAR(26) PK
actor_id      CHAR(26) NULL FK users.id ON DELETE SET NULL
actor_role    user_role NULL
action        TEXT NOT NULL            -- 'product.create','product.update','order.refund', etc.
entity_type   TEXT NOT NULL            -- 'product','order','user','coupon','category'
entity_id     CHAR(26) NULL
before_json   JSONB NULL
after_json    JSONB NULL
ip            INET NULL
user_agent    TEXT NULL
created_at    TIMESTAMPTZ DEFAULT now()
```

Append-only. Sin UPDATE ni DELETE desde la aplicación (rol de DB con permisos limitados).

### `site_settings`

Tabla key-value para configuración editable por admin:

```
key         TEXT PK                   -- 'site.name','shipping.flat_rate_cents','contact.email'
value_json  JSONB NOT NULL
updated_at  TIMESTAMPTZ DEFAULT now()
updated_by  CHAR(26) NULL FK users.id
```

## ERD simplificado

```
users ─── addresses
      ├── social_accounts
      ├── carts ── cart_items ── products
      ├── orders ── order_items ── products
      │         ├── order_status_history
      │         ├── payments
      │         └── coupon_redemptions ── coupons
      ├── wishlist_items ── products
      └── refresh_tokens

categories ─── products ── product_images ── media_files
                       └── customization_groups ── customization_options
                       └── volume_discounts

automatic_discounts ─── (category | product)

audit_log (independiente, referencia soft)
```

## Manejo de archivos 3D

Flujo estándar:

1. Admin pide URL firmada de upload (`POST /admin/uploads/presign`), con `kind=model_stl`.
2. Sube STL a R2 directo con PUT.
3. Llama `POST /admin/uploads/commit` con el `storage_key`, el backend crea registro en `media_files`.
4. Asocia a producto (`PUT /admin/products/{id}` con `model_file_id`).
5. Job en arq: `convert_stl_to_glb(media_file_id)` — descarga STL, convierte con `trimesh` + Draco, sube GLB como nuevo `media_files` con `derived_from_id` apuntando al STL.
6. Frontend consulta el GLB para preview; STL se usa solo internamente para producción.

Uploads de usuario (ENGRAVING_IMAGE, USER_FILE):

1. Frontend pide URL firmada (`POST /uploads/presign`), con `kind` apropiado.
2. Sube a R2. `media_files.owner_user_id` = usuario.
3. Al confirmar checkout, las referencias en customizations se validan: deben pertenecer al usuario y no estar ya asociadas a otra orden confirmada.

## Índices críticos

- `products(category_id, status)` para listados.
- `products USING GIN(search_tsv)`.
- `products USING GIN(tags)`.
- `orders(user_id, status, placed_at DESC)`.
- `order_items(order_id)`.
- `audit_log(entity_type, entity_id, created_at DESC)`.
- `refresh_tokens(user_id, family_id)`.
- `cart_items(cart_id)`.

## Migraciones y datos seed

Script `infra/scripts/seed.py` idempotente que crea:
- Rol admin y usuario admin inicial (email y password desde env vars).
- Categorías iniciales (las siete listadas en `product-spec.md`).
- Settings default (`site.name = 'Aura'`, `shipping.flat_rate_cents` = valor configurable, etc.).

Nunca seedear productos de prueba en producción.
