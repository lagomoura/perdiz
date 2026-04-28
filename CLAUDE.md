# Claude project guide — Aura · Impresiones 3D

Guía para sesiones de Claude Code en este repo. Para contexto persistente más detallado mirá también `.claude/memory/` y planes pasados en `.claude/plans/`.

## Qué es esto

Ecommerce de impresiones 3D con preview 3D y personalización. Monorepo:

- `apps/web/` — React 18 + Vite 5 + TS + Tailwind + shadcn/ui + zustand + react-router-dom + react-three/fiber + react-helmet-async + react-i18next.
- `apps/api/` — FastAPI + SQLAlchemy async + Alembic + Postgres + Redis + arq + boto3 (R2) + python-jose + argon2 + Resend + structlog + Sentry. Python 3.12+, gestionado con `uv`.
- `packages/api-client/` — cliente TS generado desde el OpenAPI (placeholder, regenera en CI cuando corresponda).
- `infra/` — docker-compose dev/prod, Caddyfile, scripts deploy/backup, Dockerfiles.
- `docs/` — documentación fuente-de-verdad (brand, product, architecture, devops, frontend, backend).

## Marca

- Nombre: **Aura**, descriptor **Impresiones 3D**. (Antes era p3rDiz · Soluciones 3D, rebrand 2026-04-27.)
- Logo: `apps/web/public/brand/logo.png` + favicons `favicon.ico`/`favicon-180.png`/`favicon-192.png`/`favicon-512.png`.
- Paleta brand:
  - `--brand-orange-500: #E94E1B` (primario, CTAs)
  - `--brand-orange-600: #C43C12` (hover)
  - `--brand-orange-100: #FDE0D3` (soft)
  - `--brand-amber-500: #F4B41A` (acento amarillo, gradientes)
  - `--brand-graphite-900: #1E1E1E` (lifted dark surface)
  - `--brand-graphite-700: #3A3A3A`
- **Tema dark por default**: `--neutral-0` es `#0C0C0E` (page bg) y `--neutral-900` es `#F0F0F5` (texto). Cualquier `bg-white`/`text-neutral-700`/`border-neutral-300` introducido en código nuevo es bug — usar tokens.
- Voz: tutea ("vos"/"podés"), frases cortas, técnico pero cálido, nunca solemne. Ver `docs/brand/identity.md`.

## Comandos canónicos

### Frontend

```bash
cd apps/web && npm run dev          # vite en :5173
cd apps/web && npm run build         # tsc + vite build
cd apps/web && npm run typecheck
cd apps/web && npm run lint
cd apps/web && npm run test          # vitest
```

### Backend

```bash
cd apps/api && uv run --extra dev pytest                 # tests
cd apps/api && uv run --extra dev ruff format --check .  # CI corre desde apps/api/, no desde app/
cd apps/api && uv run --extra dev ruff check .
cd apps/api && uv run --extra dev mypy app
cd apps/api && uv run uvicorn app.main:app --reload      # dev server :8000
```

### Infra local

```bash
docker compose -f infra/compose/docker-compose.dev.yml up -d
docker compose -f infra/compose/docker-compose.dev.yml down
```

DB credenciales dev: `aura:aura@localhost:5435/aura`. R2 vía MinIO en :9000, bucket `aura-media`.

### Deploy frontend (manual hasta que haya CI)

Desde `apps/web/`:

```bash
VITE_APP_ENV=production \
VITE_API_BASE_URL=https://api.aura3d.duckdns.org/v1 \
npm run build

rsync -az --delete dist/ deploy@116.203.202.6:/tmp/aura-web-dist/

ssh deploy@116.203.202.6 'docker run --rm \
  -v aura-prod_web_dist:/srv/web \
  -v /tmp/aura-web-dist:/src:ro \
  alpine sh -c "find /srv/web -mindepth 1 -delete; cp -a /src/. /srv/web/"'
```

`VITE_API_BASE_URL` se embebe en build time, no en runtime — siempre buildeá inline con la URL de prod, sin dejar `.env.production` versionado.

## Reglas de trabajo (extraídas de feedback acumulado)

- **Verificá visualmente antes de commitear** cambios de UI. Memoria `feedback_test_before_commit.md`.
- **No commitees** salvo que se pida explícito. Cuando pidan commit, no hagas push hasta que también lo pidan.
- **Heredocs por SSH dan problemas** con la indentación que pega la UI — usá `scp` o `ssh + pipe` en lugar de heredoc cuando edites archivos remotos. Ver `feedback_ssh_heredocs.md`.
- **Logo en header** mínimo h-14/h-16; tamaños actuales en producción son h-48 md:h-64 (rebrand). h-10 es ilegible. Ver `feedback_logo_size.md`.
- **Ruff format** se chequea desde `apps/api/` (no desde `apps/api/app/` o `tests/` solos). CI exige todo el árbol formateado. Ver `feedback_ruff_format_scope.md`.

## Estado de producción

VPS Hetzner CPX21, IP `116.203.202.6`, Ubuntu 24.04. Dominio temporal DuckDNS `aura3d.duckdns.org`.

- API: `https://api.aura3d.duckdns.org`
- Frontend (cuando se despliegue): `https://aura3d.duckdns.org`
- Uptime Kuma: `https://uptime.aura3d.duckdns.org`
- Path en VPS: `/opt/aura/` (compose project name `aura-prod`, image tag `aura-api:local`).
- Usuario SSH: `deploy` (sudo passwordless, en grupo docker).

**Pendiente de migrar al rebrand en VPS** (no hecho en el commit `ccac188`):
- Renombrar DB postgres `perdiz` → `aura` (dump/restore).
- Mover `/opt/perdiz` → `/opt/aura`.
- Crear bucket R2 `aura-media-prod` y copiar contenido.
- Reissue de certs Caddy con `AURA_DOMAIN=aura3d.duckdns.org`.
- Registrar `aura3d.duckdns.org` en duckdns.org apuntando al IP.

Plan completo en `.claude/plans/realizamos-un-cambio-de-zesty-sphinx.md`.

## Decisiones del catálogo

- Categorías N-level (árbol). Slugs autogenerados desde el nombre, con override opcional. Ver `project_catalog_decisions.md` en memory.

## Convenciones de commits

Estilo del repo:

- `feat(scope): descripción corta`
- `fix(scope): descripción corta`
- `chore(scope): descripción corta`

Footer obligatorio en commits hechos por Claude:

```
Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>
```

Mensajes cortos en title, detalle en body. Subject + body cuando el commit toca varias áreas.
