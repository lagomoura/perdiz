# Seguridad — Aura

Reglas vinculantes. Cualquier excepción documentada como ADR y aprobada por el usuario.

## Modelo de autenticación

### Identificadores

- Los tokens de sesión son **JWT firmados con HS256** (HMAC-SHA256).
- El secreto de firma (`JWT_SECRET`) vive solo en backend, 256 bits aleatorios, rotado anualmente o ante sospecha de fuga.
- Claims estándar: `sub` (user id ULID), `role`, `iat`, `exp`, `jti`, `iss` (`aura-api`), `aud` (`aura-web`).

### Access token

- Vida: **15 minutos**.
- Almacenamiento en cliente: **solo en memoria JS** (variable del store). **Nunca** en `localStorage` ni cookie accesible a JS.
- Enviado al backend como `Authorization: Bearer <token>`.
- Revocación: por vencimiento natural (no tenemos blacklist de access).

### Refresh token

- Vida: **14 días**.
- Almacenamiento: **cookie HttpOnly, Secure, SameSite=Lax, Path=/auth/refresh**.
- **Rotativo**: cada uso emite un nuevo refresh y marca el anterior como `revoked_at`. El nuevo apunta al viejo vía `parent_id`.
- Agrupados por `family_id`: todos los tokens de una familia derivan del login inicial.
- **Detección de reuso**: si llega un refresh token ya revocado (`revoked_at IS NOT NULL`), se revoca **toda la familia** (`family_id`) y se notifica al usuario por email. El usuario debe reloguear.
- Guardamos `token_hash` (SHA-256), nunca el token plano.

### Endpoint de refresh

`POST /auth/refresh`:
- Lee la cookie de refresh.
- Valida: existe, no expiró, no revocado, usuario activo.
- Si OK: emite nuevo access + nueva cookie de refresh, revoca el viejo.
- Si reuso detectado: 401 + revoca familia.
- Rate limit: 30 requests / minuto / IP.

### Logout

`POST /auth/logout`:
- Revoca la familia completa del refresh actual.
- Borra la cookie.
- El access vigente sigue válido hasta vencer (15 min). Se asume aceptable.

## Password

- Hashing con **argon2id**, parámetros: `time_cost=3`, `memory_cost=64 MiB`, `parallelism=1`. Ajustar si latencia de login supera 300ms consistentemente.
- Validación frontend y backend: mínimo 10 caracteres, al menos una letra y un número. Longitud máxima 128.
- Nunca loggear password ni el hash.
- El endpoint de login tiene rate limit: **10 intentos fallidos / 15 min / IP + email**. Tras 10 fallidos consecutivos en la misma cuenta, lockout de 30 minutos.

## OAuth (Google / Microsoft)

- Librería: **authlib**.
- Flow: Authorization Code + PKCE.
- Microsoft: endpoint `/common` (acepta cuentas personales y empresariales).
- Scopes mínimos: `openid email profile`.
- State parameter obligatorio, validado server-side. CSRF en esta vuelta lo cubre `state`.
- Al recibir callback: backend valida id_token firmado, extrae `sub` y `email`.
  - Si existe `social_accounts (provider, provider_sub)`: login ese usuario.
  - Si no y `users.email` coincide con el email del provider: pedir que ingrese password local para vincular (evita secuestro si alguien registra el email igual en el provider).
  - Si no existe nada: crear usuario nuevo, marcar `email_verified_at = now()` (el provider ya verificó), generar social_account.
- El email del provider **no se confía ciegamente** para altas si el usuario ya existe con password local.

## Tokens de verificación de email y reset de password

- JWT corto o token random 32 bytes base64url (elegir uno, aplicar consistente). **Guardar hash, no plain.**
- Vida: 24h (verificación), 30 min (reset).
- Un solo uso: al usar, `used_at = now()`.
- Link enviado por email. La ruta del frontend extrae el token y lo envía al backend.
- El endpoint de solicitud de reset **siempre** responde 200 "si el email existe te enviamos el link", sin revelar existencia.

## Autorización

- Cada endpoint declara explícitamente su requisito mediante dependencias FastAPI:
  - `Depends(current_user)` — cualquier usuario autenticado.
  - `Depends(current_verified_user)` — autenticado + email verificado.
  - `Depends(require_role('admin'))` — solo admin.
- **Default deny**: ruta sin dependencia de auth es pública. El lint de repo valida con un test que escanea `main.py`/routers para asegurar que toda ruta `/admin/*` tenga `require_role('admin')`.
- **Ownership**: la capa de servicio resuelve permisos sobre recursos (ej. `order.user_id == current_user.id OR admin`). Nunca confiar en IDs del path sin chequear pertenencia.
- **Rutas admin responden 404** a no-admins (ver `product/roles-and-permissions.md`).

## Sesiones concurrentes

- Un usuario puede tener múltiples refresh tokens activos (varios dispositivos/navegadores), cada uno con su `family_id`.
- En `/mi-cuenta/seguridad` se listan las sesiones con fecha y user agent; permite revocar selectivamente (marca `revoked_at` en la familia). MVP puede entregar esta pantalla sin la vista pero con el endpoint listo.

## CORS

- En desarrollo: `http://localhost:5173`.
- En producción: **solo** el dominio oficial configurado en `ALLOWED_ORIGINS` (env). Sin `*`.
- Métodos permitidos: `GET, POST, PUT, PATCH, DELETE, OPTIONS`.
- Headers permitidos: `Authorization, Content-Type, Idempotency-Key`.
- `allow_credentials=True` para que el refresh cookie viaje en `/auth/refresh`.

## CSRF

- Como el access token va en header (no cookie), el endpoint general está protegido contra CSRF por diseño.
- El único endpoint expuesto a CSRF es `/auth/refresh` (cookie automática). Se mitiga con:
  - `SameSite=Lax` (previene cross-site en POST, permite top-level GETs).
  - Validación de `Origin` header: debe coincidir con `ALLOWED_ORIGINS`. Rechazo con 403 si no.
  - El endpoint solo emite tokens, no muta otros recursos del usuario.

## Rate limiting

Librería: **slowapi** (`@limiter.limit(...)`). Redis como backend compartido entre workers.

| Endpoint | Límite |
|---|---|
| `POST /auth/login` | 10/15min por (IP + email) |
| `POST /auth/register` | 5/hora por IP |
| `POST /auth/password/forgot` | 3/hora por IP |
| `POST /auth/password/reset` | 10/hora por IP |
| `POST /auth/refresh` | 30/min por IP |
| `POST /uploads/presign` | 20/min por usuario |
| `POST /webhooks/*` | sin límite de slowapi (se valida firma) |
| Endpoints de lectura pública | 300/min por IP |
| Endpoints de escritura autenticada | 120/min por usuario |
| `/admin/*` | 300/min por usuario |

Respuesta de rate-limit: 429 con `Retry-After` header.

## Webhooks

- Cada pasarela firma sus webhooks. Backend **siempre** valida firma **antes** de parsear o actuar.
  - MercadoPago: firma por secret compartido, validación según docs oficiales.
  - Stripe: `Stripe-Signature` con `whsec_...`.
  - PayPal: verificación vía API `verify-webhook-signature`.
- Idempotencia: cada webhook trae un `event_id`; persistir y rechazar duplicados.
- Rechazos devuelven 400 (nunca 200 silencioso para no decirle al atacante qué fue mal).

## Subida de archivos

- **Todo upload va con URL firmada pre-generada por el backend** (POST presign → PUT a R2). El frontend nunca recibe credenciales S3.
- URL firmada TTL: **10 minutos**.
- Validaciones backend en el presign:
  - `mime_type` en allowlist (por `kind`).
  - `size_bytes` declarado ≤ máximo por `kind` (imagen 5MB, STL/OBJ 100MB).
- Validaciones en `commit`:
  - `HEAD` el objeto en R2: existe, `Content-Length` ≤ máx.
  - Para imágenes: verificar firma mágica (magic bytes) coincide con mime declarado.
  - Para STL/OBJ: verificar que al menos los primeros bytes son parseable por `trimesh` (fail-fast).
- Uploads de usuario no usados en 24h se limpian por job.

## Logs y PII

- Nunca loggear: passwords, tokens plain, refresh cookies, números completos de tarjeta (no manejamos tarjetas directamente: pasa todo por pasarela), DNIs.
- Emails pueden loggearse pero enmascarados: `j***@gmail.com`.
- Los JSON de webhook recibidos se guardan en `payments.raw_webhook_events`, en DB; sin pasar por logs.
- Sentry: scrubbing activo de campos comunes (password, secret, token, cookie, authorization).

## Auditoría

- Toda mutación en `/admin/*` dispara una escritura a `audit_log` vía dependencia FastAPI.
- Entidades auditadas: `products`, `categories`, `orders`, `users`, `coupons`, `automatic_discounts`, `site_settings`, `customization_groups/options`.
- El admin **no puede modificar ni borrar** registros de `audit_log` desde la app. El rol de DB usado por la app tiene `INSERT, SELECT` sobre esa tabla, sin `UPDATE/DELETE`.
- Campos `before_json` y `after_json` se scrubbean antes de guardar (remueven passwords, tokens).

## Endurecimiento de infra

- Caddy ofrece TLS automático (Let's Encrypt), HSTS, HTTP/2.
- Puertos expuestos al exterior: solo 80 y 443.
- Postgres y Redis escuchan solo en la red Docker interna.
- SSH con auth por clave, sin password. Usuario no-root. Fail2ban.
- Backups cifrados en R2 (objeto en bucket con SSE-KMS o KMS gestionado por Cloudflare).
- Secretos en VPS en archivo `.env` con permisos `0600`, propiedad del usuario de deploy. Nunca en el repo.
- Imágenes Docker pineadas por tag + digest.

## Headers de respuesta

FastAPI aplica middleware con:

```
Strict-Transport-Security: max-age=31536000; includeSubDomains
X-Content-Type-Options: nosniff
X-Frame-Options: DENY
Referrer-Policy: strict-origin-when-cross-origin
Permissions-Policy: geolocation=(), camera=(), microphone=()
Content-Security-Policy: default-src 'self'; img-src 'self' https://*.r2.dev data:;
                         style-src 'self' 'unsafe-inline' https://fonts.googleapis.com;
                         font-src 'self' https://fonts.gstatic.com;
                         script-src 'self';
                         connect-src 'self' https://api.aura.ar https://*.sentry.io;
                         frame-ancestors 'none';
```

Exacto dominio R2 y `connect-src` se ajustan por ambiente. CSP en modo `report-only` durante la primera semana de producción para descubrir falsos positivos.

## Rotación de secretos

- `JWT_SECRET`: rotación anual, plan de rotación: nuevo secreto convive como `JWT_SECRET_NEXT`; ventana de 1 hora donde se aceptan ambos en validación; tras la ventana, solo el nuevo.
- Credenciales R2, Postgres, Resend, Sentry, OAuth: rotables manualmente. Procedimiento documentado en `devops/deployment.md`.
