# Deployment — Aura

Infra pragmática para MVP en Hetzner. Single-node, Docker Compose, coste mínimo.

## Hardware inicial

- **Hetzner CPX21**: 3 vCPU, 4 GB RAM, 80 GB disco. ~€8/mes.
- Ubuntu 24.04 LTS.
- Imagen base minimal + UFW activa: 22 (SSH), 80, 443.

Escalar a CPX31 o separar Postgres a Hetzner Cloud DB cuando la DB o la app muestren saturación sostenida (>70% CPU o p95 de requests >300ms).

## Topología de contenedores

`infra/compose/docker-compose.prod.yml`:

```
services:
  caddy         # reverse proxy + TLS + sirve apps/web como estático
  api           # uvicorn con apps/api
  worker        # arq worker (misma imagen que api, distinto entrypoint)
  postgres      # Postgres 16
  redis         # Redis 7
  backup        # contenedor cron que dumpea Postgres a R2
  uptime-kuma   # dashboard de uptime (puerto interno; accesible vía caddy con basic auth)
```

Red Docker interna única (`perdiz_internal`). Solo `caddy` expone puertos al host.

## Archivos de infra

```
infra/
├── docker/
│   ├── api.Dockerfile
│   ├── web.Dockerfile       # build estático; el resultado se monta en caddy
│   └── worker.Dockerfile    # opcional si se comparte con api
├── compose/
│   ├── docker-compose.prod.yml
│   ├── docker-compose.staging.yml
│   └── docker-compose.dev.yml
├── caddy/
│   └── Caddyfile
└── scripts/
    ├── deploy.sh
    ├── backup.sh
    ├── restore.sh
    └── rotate_secret.sh
```

## Caddyfile (producción, resumen)

```
aura.ar {
  encode zstd gzip
  header {
    Strict-Transport-Security "max-age=31536000; includeSubDomains"
    X-Content-Type-Options "nosniff"
    Referrer-Policy "strict-origin-when-cross-origin"
    Permissions-Policy "geolocation=(), camera=(), microphone=()"
  }
  root * /srv/web
  try_files {path} /index.html
  file_server
}

api.aura.ar {
  encode zstd gzip
  reverse_proxy api:8000
}

uptime.aura.ar {
  basicauth {
    admin {env.UPTIME_BASIC_AUTH_HASH}
  }
  reverse_proxy uptime-kuma:3001
}
```

## Dockerfiles

### `api.Dockerfile`

- Imagen base `python:3.12-slim`.
- Usuario no-root.
- Instala dependencias con `uv sync --frozen --no-dev`.
- Copia `app/` y `alembic/`.
- Entrypoint: `alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 3`.

### `worker.Dockerfile`

Igual que API pero entrypoint `arq app.tasks.worker.WorkerSettings`.

### `web.Dockerfile`

Multi-stage:
1. `node:20-alpine` → `npm ci && npm run build` → artefactos en `/dist`.
2. `scratch` o Caddy nativo sirve el directorio `/dist`; se monta como volumen en el servicio `caddy` en compose.

## CI/CD — GitHub Actions

```
.github/workflows/
├── ci-api.yml          # lint, type, test backend cuando cambia apps/api
├── ci-web.yml          # lint, type, test frontend cuando cambia apps/web
├── ci-api-client.yml   # regenera packages/api-client desde OpenAPI y abre PR si hay drift
├── deploy-staging.yml  # al push a main → build + deploy staging
└── deploy-prod.yml     # al publish de release tag vX.Y.Z → deploy prod
```

### Flujo deploy

1. Job `build`:
   - Checkout.
   - Setup Python + uv o Node 20.
   - Corre tests y linting.
   - Build imagen Docker con tag `ghcr.io/<org>/aura-api:<sha>` y `:latest-staging` o `:latest-prod`.
   - Push a GHCR.
2. Job `deploy` (sshaction):
   - Conecta al VPS como usuario `deploy`.
   - `cd /opt/aura && git pull`.
   - `docker compose pull && docker compose up -d --remove-orphans`.
   - Alembic corre en entrypoint del contenedor api.
   - Healthcheck post-deploy: hace `GET /health/deep`; si falla, hace rollback al tag anterior.
3. Notificación (opcional): Slack/email.

### Build del frontend

- Construir **con `VITE_*` de prod** en el job de build.
- Publicar los assets estáticos al servidor (sobreescribiendo volumen `web_dist`).
- Caddy sirve desde ese volumen; SPA con fallback `index.html`.

### Secrets de GHA

Por entorno (`staging`, `production`):
- `SSH_HOST`, `SSH_USER`, `SSH_KEY`.
- `GHCR_TOKEN` (o `GITHUB_TOKEN` con permisos a packages).
- `*_API_KEY`, etc. para pasar a archivo `.env` remoto si aplica.

## Postgres en Docker

- Imagen `postgres:16-alpine`.
- Volumen `aura_pgdata:/var/lib/postgresql/data`.
- Variables `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`.
- `shared_buffers`, `work_mem` ajustados en `postgresql.conf` montado.
- Usuario de aplicación **no superuser**, con permisos mínimos (SELECT/INSERT/UPDATE/DELETE en tablas de app, INSERT/SELECT en `audit_log`).
- Script de seed al primer arranque crea DB, rol y GRANTs.

## Redis en Docker

- `redis:7-alpine`, `appendonly yes`, volumen persistente (`aura_redisdata`).

## Backups

Contenedor `backup`:

- Cron interno: diario 03:00 UTC (00:00 ART).
- `pg_dump -Fc` → comprime → encripta con `age` → sube a bucket R2 `aura-backups` con key `postgres/{YYYY}/{MM}/{DD}.dump.age`.
- Retención: 30 diarios + 12 mensuales (keep-first-of-month). Script de purga corre al final del backup.
- Semana 1 tras ir a prod: **verificar restore** con el script `restore.sh` en staging.

R2 buckets recomendados:
- `aura-media-prod` — media pública (imágenes, GLB) con CORS apropiado.
- `aura-media-private` — uploads de usuario + STL originales, sin public access.
- `aura-backups` — backups cifrados, sin public access.

## Caddyfile + volumes (compose extracto)

```yaml
services:
  caddy:
    image: caddy:2-alpine
    restart: unless-stopped
    ports: ["80:80", "443:443"]
    volumes:
      - ./caddy/Caddyfile:/etc/caddy/Caddyfile:ro
      - web_dist:/srv/web:ro
      - caddy_data:/data
      - caddy_config:/config

volumes:
  aura_pgdata:
  aura_redisdata:
  web_dist:
  caddy_data:
  caddy_config:
```

## Releases

- Usamos **tags semver** en main para disparar deploy a prod.
- Commits en main van a staging automáticamente.
- Changelog en `CHANGELOG.md` actualizado por PRs (Conventional Commits facilita automatizar con `git-cliff`).

## Rotación de secretos — procedimiento

Para cualquier secret (p.ej. `R2_SECRET_ACCESS_KEY`):

1. Crear nueva credencial en el provider sin eliminar la vieja.
2. Actualizar `/opt/aura/.env.production` en VPS con el nuevo valor.
3. `docker compose up -d --no-deps api worker` (reinicia solo lo necesario).
4. Verificar logs limpios.
5. Revocar la credencial vieja en el provider.
6. Registrar el cambio en auditoría interna (fecha, quién, por qué).

Para `JWT_SECRET` usar el mecanismo `JWT_SECRET_NEXT` documentado en `architecture/security.md`.

## Monitoreo post-deploy

- Sentry recibe errores de frontend y backend.
- Uptime Kuma pinguea `/health` cada 60s y alerta por email.
- Log aggregation inicialmente via `docker logs`; si crece, agregar Loki + Promtail como extensión futura.

## Rollback

- Imagen Docker anterior queda en GHCR con tag de commit.
- `SSH a VPS` → editar tag en compose → `docker compose up -d`.
- Si hay migración que bloquea, se hace **rollback de código** a la última versión **que sea compatible con el schema actual**; las migraciones destructivas requieren plan de down-migration explícito y revisión previa.

## Lista de verificación antes de primer deploy a prod

- [ ] Dominio registrado y DNS apuntando.
- [ ] Certificados TLS emitidos (Caddy lo hace automático al primer hit).
- [ ] `.env.production` completo y cargado en VPS.
- [ ] Secretos de GHA configurados por entorno.
- [ ] Backup job probado con restore exitoso en staging.
- [ ] Sentry recibiendo eventos de prueba.
- [ ] Webhooks de pasarelas configurados y probados end-to-end en staging.
- [ ] OAuth con redirect URIs de prod agregadas a Google y Microsoft.
- [ ] `BOOTSTRAP_ADMIN_EMAIL` y password generados; cambio inmediato tras primer login.
- [ ] Términos, privacidad, FAQ publicados.
- [ ] CSP en `report-only` la primera semana.
- [ ] Uptime Kuma conectado.
- [ ] Smoke E2E en staging pasa.
