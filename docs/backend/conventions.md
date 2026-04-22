# Backend — convenciones

Vinculante para todo código en `apps/api`. Pensado para que múltiples agentes trabajen en paralelo sin divergir.

## Stack y versiones

- Python 3.12
- FastAPI 0.110+
- SQLAlchemy 2.x async
- Pydantic 2.x
- Alembic 1.13+
- uv (package manager)
- ruff (lint + format)
- mypy strict
- pytest + pytest-asyncio

## Estructura de directorios

```
apps/api/
├── pyproject.toml
├── uv.lock
├── alembic.ini
├── alembic/
│   ├── env.py
│   └── versions/
├── app/
│   ├── __init__.py
│   ├── main.py                # crea app, registra routers, middlewares, errores
│   ├── config.py              # Settings (pydantic-settings) + lectura de env
│   ├── logging.py             # setup structlog JSON
│   ├── observability.py       # Sentry init, trace IDs
│   ├── db/
│   │   ├── session.py         # engine, async session, dependency get_db
│   │   ├── base.py            # declarative base + mixins (TimestampMixin, SoftDeleteMixin, ULIDMixin)
│   │   └── types.py           # ULID type, CITEXT type
│   ├── models/                # SQLAlchemy ORM models (archivos por entidad)
│   │   ├── user.py
│   │   ├── product.py
│   │   └── ...
│   ├── schemas/               # Pydantic v2 schemas (request/response)
│   │   ├── user.py
│   │   ├── product.py
│   │   └── ...
│   ├── api/
│   │   ├── deps.py            # dependencies (current_user, require_role, audit)
│   │   ├── errors.py          # exception handlers
│   │   └── v1/
│   │       ├── __init__.py    # APIRouter raíz v1, include de sub-routers
│   │       ├── auth.py
│   │       ├── users.py
│   │       ├── categories.py
│   │       ├── products.py
│   │       ├── cart.py
│   │       ├── orders.py
│   │       ├── wishlist.py
│   │       ├── uploads.py
│   │       ├── webhooks.py
│   │       └── admin/
│   │           ├── __init__.py
│   │           ├── products.py
│   │           ├── categories.py
│   │           ├── orders.py
│   │           ├── users.py
│   │           ├── coupons.py
│   │           ├── settings.py
│   │           └── audit.py
│   ├── services/              # lógica de negocio, una clase/módulo por dominio
│   │   ├── auth/
│   │   │   ├── tokens.py
│   │   │   ├── oauth.py
│   │   │   └── passwords.py
│   │   ├── catalog/
│   │   ├── cart/
│   │   ├── orders/
│   │   ├── payments/
│   │   │   ├── mercadopago.py
│   │   │   ├── stripe.py
│   │   │   └── paypal.py
│   │   ├── customization/
│   │   │   ├── validators.py
│   │   │   └── registry.py
│   │   ├── discounts/
│   │   ├── media/
│   │   │   ├── r2_client.py
│   │   │   └── stl_to_glb.py
│   │   ├── email/
│   │   │   ├── resend.py
│   │   │   └── templates/
│   │   └── audit.py
│   ├── repositories/          # acceso a DB (CRUD, queries complejas)
│   │   ├── base.py
│   │   ├── users.py
│   │   └── ...
│   ├── exceptions.py          # jerarquía de errores de dominio
│   ├── tasks/                 # jobs arq
│   │   ├── worker.py
│   │   ├── media.py
│   │   ├── orders.py
│   │   └── emails.py
│   └── utils/                 # helpers sin dependencias de dominio
│       ├── ulid.py
│       ├── slug.py
│       └── masking.py
├── tests/
│   ├── conftest.py            # fixtures: db, client, user_factory, etc.
│   ├── integration/
│   ├── unit/
│   └── e2e/
└── Dockerfile
```

## Capas y responsabilidades

Flujo de una request: **Router → Dependencia de auth/validación → Service → Repository → DB**.

- **Router (`app/api/v1/*.py`)**: valida payload con Pydantic, llama a un método de service, serializa respuesta. **Nunca** consulta DB directamente, **nunca** implementa lógica de negocio.
- **Service (`app/services/*`)**: toda la lógica. Coordina repositories, valida reglas, emite eventos, llama a providers externos. **No** recibe tipos de FastAPI ni de Pydantic excepto DTOs propios si se necesitan.
- **Repository (`app/repositories/*`)**: solo I/O con DB. CRUD, queries, filtros. Recibe criterios, devuelve modelos ORM o DTOs internos. **Nunca** importa FastAPI.
- **Models (`app/models/*`)**: SQLAlchemy ORM. Nada de lógica más allá de `__repr__` y helpers triviales.
- **Schemas (`app/schemas/*`)**: Pydantic. Request/Response DTOs. Nunca se usan en capa service excepto como estructuras puras de datos.

Regla simple: **nunca saltearse una capa hacia adentro**. Un router no toca repository. Un service no toca la DB directamente.

## Naming

- Archivos, módulos: `snake_case.py`.
- Clases: `PascalCase`.
- Funciones, métodos, variables: `snake_case`.
- Constantes: `UPPER_SNAKE_CASE`.
- SQL enums: `snake_case` (`order_status`, `user_role`).
- Endpoints: kebab-case en URL (`/auth/password/forgot`), parámetros de path siempre `{entity_id}` (singular) con ULID.
- Tablas DB: `snake_case` plural.
- Tests: `test_<feature>_<behavior>.py`, función `test_<expected_behavior>`.

## Configuración

- Todo viene de **env vars** (12-factor). Leídas con `pydantic-settings`.
- `app/config.py` expone `settings` singleton.
- **Prohibido** leer `os.environ` fuera de `config.py`.
- Valores sin default razonable: el backend **falla al arrancar** si faltan. No hay defaults mágicos en prod.
- Categorías de variables:
  - `APP_*` (entorno, debug, URLs)
  - `DB_*` (conexión Postgres)
  - `REDIS_URL`
  - `JWT_SECRET`, `JWT_SECRET_NEXT?`
  - `OAUTH_GOOGLE_*`, `OAUTH_MICROSOFT_*`
  - `R2_*` (account id, access key, secret, bucket, public url base)
  - `MERCADOPAGO_*`, `STRIPE_*`, `PAYPAL_*`
  - `RESEND_API_KEY`, `EMAIL_FROM`
  - `SENTRY_DSN`
  - `ALLOWED_ORIGINS` (CSV)

Ver `devops/environments.md` para la lista canónica.

## Errores

### Jerarquía de excepciones

```
AppError                         (base, todas heredan de esta)
├── DomainError                  (400-422 típicamente)
│   ├── ValidationError
│   ├── BusinessRuleViolation
│   └── ResourceConflict
├── AuthError                    (401)
├── AuthorizationError           (403/404 para admin)
├── NotFoundError                (404)
├── RateLimitError               (429)
└── ExternalServiceError         (502/503)
```

Cada subclase lleva un **`code`** estable (constante) y mensaje español listo para UI.

### Códigos de error estables

Formato: `<DOMAIN>_<REASON>` en UPPER_SNAKE. Ejemplos:

- `AUTH_INVALID_CREDENTIALS`
- `AUTH_EMAIL_NOT_VERIFIED`
- `AUTH_ACCOUNT_LOCKED`
- `CART_ITEM_OUT_OF_STOCK`
- `CART_ITEM_PRICE_CHANGED`
- `CUSTOMIZATION_REQUIRED_GROUP_MISSING`
- `CUSTOMIZATION_INVALID_OPTION`
- `CUSTOMIZATION_FILE_TOO_LARGE`
- `COUPON_EXPIRED`
- `COUPON_MIN_ORDER_NOT_MET`
- `ORDER_INVALID_STATE_TRANSITION`
- `PAYMENT_WEBHOOK_INVALID_SIGNATURE`
- `UPLOAD_MIME_NOT_ALLOWED`

La lista canónica vive en `app/exceptions.py` como constantes. Frontend consume este set para traducciones.

### Formato de respuesta de error

```json
{
  "error": {
    "code": "CART_ITEM_OUT_OF_STOCK",
    "message": "Uno de los productos de tu carrito se quedó sin stock.",
    "details": {
      "product_id": "01HWXYZ..."
    },
    "request_id": "01HW..."
  }
}
```

- `details` es un objeto opcional con contexto útil para UI.
- `request_id` es el trace ID generado por middleware; incluirlo en todos los logs.
- Handlers FastAPI: registrar uno por clase de excepción; jamás devolver 500 con stack trace al cliente.

## Respuestas de éxito

- Colección: siempre paginada, envelope:
  ```json
  {
    "data": [...],
    "pagination": { "cursor": "...", "next_cursor": "...", "has_more": true, "count": 24 }
  }
  ```
- Single: objeto directo, sin envelope. El tipo se deriva del schema Pydantic.
- 201 Created para inserts; 200 para updates que devuelven recurso; 204 No Content para operaciones sin respuesta útil.

## Validación

- Entrada: **Pydantic v2** con `ConfigDict(extra='forbid')` por default (rechaza campos desconocidos).
- Constraints declarativos (`Field(min_length=...)`, `constr(...)`, `field_validator`).
- Reglas de negocio van en service, no en schemas.
- Nunca aceptar campos `role`, `status`, `created_at` desde el cliente; esos los controla el backend.

## JWT y sesiones — implementación

- Módulo `app/services/auth/tokens.py` expone:
  - `create_access_token(user)`
  - `create_refresh_token(user) → (plaintext, db_row)`
  - `verify_access_token(token) → TokenPayload`
  - `rotate_refresh_token(plaintext) → (new_plaintext, new_db_row)` (gestiona detección de reuso)
  - `revoke_family(family_id)`
- Dependencies FastAPI en `app/api/deps.py`:
  - `get_token(request)` extrae `Authorization: Bearer`.
  - `current_user(token, db)` retorna `User` o lanza `AuthError`.
  - `current_verified_user` suma check de `email_verified_at`.
  - `require_role(role)` factory que retorna un `Depends`.

## Migraciones

- Una migración Alembic por PR cuando haya cambio de schema. Nombre descriptivo (`2026_04_22_add_products_table.py`).
- **Autogenerar y revisar**: `alembic revision --autogenerate -m "..."`; siempre leer el archivo generado. Alembic omite algunos cambios (renombres, constraints exóticos).
- Migraciones idempotentes no son requeridas pero sí **reversibles**: definir `downgrade()`. Excepción: data migrations destructivas deben documentarse con comentario explicando por qué no se revierten.
- **Nunca** ejecutar DDL fuera de Alembic en prod.
- Aplicar migraciones automáticamente en el entrypoint del contenedor API (`alembic upgrade head`) antes de arrancar uvicorn.

## Base de datos — patrones

- Sesiones async: `AsyncSession` inyectada por `Depends(get_db)`. Transacción por request: commit al final si no hubo excepción.
- `select(Model).where(...)` siempre con tipos; evitar raw SQL salvo casos puntuales (full-text search con `ts_rank`).
- **N+1**: detectable con `sqlalchemy.events` en tests. Tests de endpoints incluyen assert de "máximo N queries".
- `scalars().all()` para listas, `scalar_one_or_none()` para opcional, `scalar_one()` cuando no existir es error.
- Para queries con muchos joins que explotan a nivel performance, usar views o funciones en Postgres como último recurso; documentarlo en data-model.

## Background jobs (arq)

- Worker aparte, contenedor independiente.
- Redis como broker.
- Tareas principales: `convert_stl_to_glb`, `send_email`, `reconcile_payment`, `cleanup_abandoned_uploads`, `cleanup_abandoned_carts`.
- Cada tarea debe ser **idempotente**: recibir un id, actuar, tolerante a reejecución.
- Timeouts explícitos por tarea.
- Reintentos: 3 con backoff exponencial. Al fallar definitivamente, registrar en `failed_jobs` (tabla Postgres) y notificar Sentry.

## Logs

- **structlog** con renderer JSON.
- Middleware agrega `request_id`, `method`, `path`, `status`, `duration_ms`, `user_id` si aplica, `ip`.
- Nivel default: `INFO`. En dev, `DEBUG` permitido.
- Scrubbing de campos sensibles antes de emitir.
- Salida a stdout; Docker lo captura.

## Testing

### Pirámide

- **Unit**: services con dependencias mockeadas. Rápidos. Cobertura principal de lógica.
- **Integration**: endpoints contra DB real (testcontainers-postgres), sin mocks. Cubre happy path + errores de dominio clave por endpoint.
- **E2E**: pocos, críticos. Flujo completo: registro → verificación → login → agregar carrito → checkout simulado (pasarelas mockeadas).

### Reglas

- Todo endpoint tiene **al menos 1 integration test**.
- Todo service con lógica no-trivial tiene unit tests.
- Tests nunca comparten estado. Fixtures crean DB limpia por función (usar `pytest-postgresql` truncate-per-test) o transacción rollback.
- Pasarelas y Resend se mockean en tests (`responses` o `respx`).
- R2 en tests: MinIO levantado por testcontainers.
- **No** tests que llamen servicios externos reales.
- Cobertura objetivo: 80% líneas en `app/services/` y `app/api/`. Se mide, no se agrega código solo para subir cobertura.

## Linting y type check

- `ruff check .` (reglas: `E, F, I, UP, B, SIM, PL, RUF`).
- `ruff format .` (reemplaza Black).
- `mypy --strict app/` (no `Any` implícito, retornos obligatorios).
- Hooks de pre-commit: ruff, mypy, pytest-changed (opcional).
- CI falla si cualquier check falla.

## Commits y PRs

- **Conventional Commits**: `feat:`, `fix:`, `chore:`, `refactor:`, `docs:`, `test:`, `ci:`, `build:`, `perf:`.
- Scope opcional: `feat(cart): prevent adding out-of-stock items`.
- PRs con descripción que explique el **por qué**. Checklist de: tests pasan, migraciones aplicadas, docs actualizados si corresponde.
- Un PR idealmente < 400 líneas cambiadas. Si excede, split en PRs encadenados.

## Seguridad en código

- **Nunca** concatenar strings en SQL. SQLAlchemy parametriza; usar sus APIs.
- Sanitizar HTML en `description` de producto con `bleach` allowlist reducida (tags: `b,i,u,strong,em,p,br,ul,ol,li,a[href]`).
- Headers estrictos configurados en middleware (ver `architecture/security.md`).
- **Principio de menor privilegio**: el usuario de DB que usa la app no es superusuario; tiene `SELECT/INSERT/UPDATE/DELETE` en tablas de app, `SELECT/INSERT` en `audit_log`.

## Performance

- Async en todo el stack.
- Uvicorn con 2–4 workers en producción (ajustable según VPS).
- Connection pool SQLAlchemy: `pool_size=10`, `max_overflow=20`.
- Cache de lectura opcional en Redis (productos, categorías populares) — **no agregar en MVP inicial**; medir primero.
