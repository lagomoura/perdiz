# Entornos y variables — p3rDiz

## Entornos definidos

| Entorno | Propósito | URL frontend | URL API |
|---|---|---|---|
| `development` | máquina del desarrollador | `http://localhost:5173` | `http://localhost:8000` |
| `staging` | pruebas pre-prod, integración con sandboxes de pasarelas | `https://staging.perdiz.ar` | `https://api.staging.perdiz.ar` |
| `production` | público | `https://perdiz.ar` | `https://api.perdiz.ar` |

**Nota dominio**: todavía sin comprar. Sustituir `perdiz.ar` por el dominio final cuando se defina.

## Variables de entorno — backend (`apps/api`)

### Aplicación

| Variable | Descripción | Ejemplo |
|---|---|---|
| `APP_ENV` | `development` / `staging` / `production` | `production` |
| `APP_DEBUG` | booleano | `false` |
| `APP_BASE_URL` | URL pública del API | `https://api.perdiz.ar` |
| `WEB_BASE_URL` | URL pública del front (para links en emails, callbacks) | `https://perdiz.ar` |
| `ALLOWED_ORIGINS` | CSV de orígenes permitidos | `https://perdiz.ar` |

### Base de datos

| Variable | Descripción |
|---|---|
| `DB_URL` | DSN async `postgresql+asyncpg://user:pass@host:5432/dbname` |
| `DB_POOL_SIZE` | default 10 |
| `DB_MAX_OVERFLOW` | default 20 |

### Redis (arq + rate limit)

| Variable | Descripción |
|---|---|
| `REDIS_URL` | `redis://redis:6379/0` |

### Auth / JWT

| Variable | Descripción |
|---|---|
| `JWT_SECRET` | 256 bits aleatorios (base64) |
| `JWT_SECRET_NEXT` | opcional, durante ventana de rotación |
| `JWT_ACCESS_TTL_SECONDS` | default `900` (15 min) |
| `JWT_REFRESH_TTL_SECONDS` | default `1209600` (14 días) |

### OAuth

| Variable | Descripción |
|---|---|
| `OAUTH_GOOGLE_CLIENT_ID` | |
| `OAUTH_GOOGLE_CLIENT_SECRET` | |
| `OAUTH_GOOGLE_REDIRECT_URL` | `{APP_BASE_URL}/v1/auth/oauth/google/callback` |
| `OAUTH_MICROSOFT_CLIENT_ID` | |
| `OAUTH_MICROSOFT_CLIENT_SECRET` | |
| `OAUTH_MICROSOFT_TENANT` | `common` |
| `OAUTH_MICROSOFT_REDIRECT_URL` | `{APP_BASE_URL}/v1/auth/oauth/microsoft/callback` |

### Cloudflare R2

| Variable | Descripción |
|---|---|
| `R2_ACCOUNT_ID` | |
| `R2_ACCESS_KEY_ID` | |
| `R2_SECRET_ACCESS_KEY` | |
| `R2_BUCKET` | `perdiz-media-prod` |
| `R2_PUBLIC_BASE_URL` | URL pública del bucket (si `public`), o CDN custom |
| `R2_REGION` | `auto` |

### Pagos

| Variable | Descripción |
|---|---|
| `MERCADOPAGO_ACCESS_TOKEN` | prod o sandbox según ambiente |
| `MERCADOPAGO_WEBHOOK_SECRET` | |
| `STRIPE_SECRET_KEY` | |
| `STRIPE_WEBHOOK_SECRET` | |
| `PAYPAL_CLIENT_ID` | |
| `PAYPAL_CLIENT_SECRET` | |
| `PAYPAL_MODE` | `sandbox` / `live` |

### Email

| Variable | Descripción |
|---|---|
| `RESEND_API_KEY` | |
| `EMAIL_FROM` | `p3rDiz <hola@perdiz.ar>` |
| `EMAIL_SUPPORT` | `soporte@perdiz.ar` |

### Observabilidad

| Variable | Descripción |
|---|---|
| `SENTRY_DSN` | |
| `SENTRY_TRACES_SAMPLE_RATE` | `0.1` prod, `1.0` staging, `0` dev |
| `LOG_LEVEL` | `INFO` prod, `DEBUG` dev |

### Admin bootstrap (seed)

| Variable | Descripción |
|---|---|
| `BOOTSTRAP_ADMIN_EMAIL` | email que el seed promueve a admin |
| `BOOTSTRAP_ADMIN_PASSWORD` | password inicial (cambiar tras primer login) |

## Variables de entorno — frontend (`apps/web`)

Vite inyecta solo vars prefijadas con `VITE_`:

| Variable | Descripción |
|---|---|
| `VITE_APP_ENV` | `development` / `staging` / `production` |
| `VITE_API_BASE_URL` | `https://api.perdiz.ar/v1` |
| `VITE_SENTRY_DSN` | DSN de frontend (distinto del de backend) |
| `VITE_MERCADOPAGO_PUBLIC_KEY` | pública |
| `VITE_STRIPE_PUBLISHABLE_KEY` | pública |
| `VITE_PAYPAL_CLIENT_ID` | pública |
| `VITE_GOOGLE_OAUTH_CLIENT_ID` | pública |
| `VITE_MICROSOFT_OAUTH_CLIENT_ID` | pública |

## Archivos `.env`

```
.env.example               versionado, documenta variables sin secretos
.env.development           versionado (sin secretos), usado en dev local
.env.local                 NO versionado, override local del dev
.env.staging               NO versionado (está en servidor)
.env.production            NO versionado (está en servidor)
```

`.gitignore` excluye `.env`, `.env.local`, `.env.*.local`, `.env.staging`, `.env.production`.

`.env.example` es la fuente de verdad de qué variables existen. CI valida que el set de variables no tenga drift.

## Gestión de secretos

- **Dev**: archivos locales. Generar un `.env.local` desde `.env.example` al clonar.
- **CI (GitHub Actions)**: secrets del repo. Categorizados por ambiente con entornos de GHA (`staging`, `production`).
- **VPS (Hetzner)**: archivo `/opt/perdiz/.env.{staging|production}` con permisos `0600`, propietario del usuario `deploy`. Cargado por docker compose con `env_file`.
- **Rotación**: procedimiento documentado en `devops/deployment.md`. Secretos expuestos se rotan inmediatamente; el sistema debe funcionar durante la rotación con la estrategia `_NEXT` descrita en `architecture/security.md`.

## Servicios externos — cómo conseguir credenciales

- **Cloudflare R2**: crear cuenta, bucket, API token con permisos de Object Read/Write al bucket.
- **Resend**: alta, verificar dominio SPF/DKIM, API key.
- **Sentry**: proyecto para `apps/api` (backend) y otro para `apps/web` (frontend).
- **MercadoPago**: cuenta, credencials de aplicación, configurar URL de webhook.
- **Stripe**: cuenta, webhook secret, configurar eventos `checkout.session.completed`, `charge.refunded`.
- **PayPal**: developer account, REST app, webhook.
- **Google OAuth**: consola GCP, credenciales OAuth 2.0, URIs de redirect autorizadas.
- **Microsoft OAuth**: Azure AD App registration, redirect URI, permisos `User.Read`.

## Dominios y DNS

Cuando se compre el dominio:
- `perdiz.ar` → VPS Hetzner (A record).
- `www.perdiz.ar` → redirect a `perdiz.ar` (Caddy).
- `api.perdiz.ar` → VPS (A record).
- `staging.perdiz.ar` y `api.staging.perdiz.ar` → mismo VPS o subVPS.
- `media.perdiz.ar` (opcional) → CNAME a bucket R2 custom domain.
- SPF/DKIM/DMARC para emails Resend.

## Timezone del proceso

`TZ=UTC` en todos los contenedores. La UI traduce a `America/Argentina/Buenos_Aires` en cliente.
