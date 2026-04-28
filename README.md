# Aura — Impresiones 3D

Ecommerce de impresiones 3D. Monorepo con frontend React + backend FastAPI.

## Documentación

Antes de tocar código, leer `docs/README.md`. Toda convención, contrato y regla está ahí.

## Layout del monorepo

```
apps/
  web/          Frontend React + TypeScript + Vite
  api/          Backend FastAPI + SQLAlchemy async
packages/
  api-client/   Cliente TypeScript generado desde OpenAPI (CI)
infra/
  docker/       Dockerfiles
  compose/      docker-compose (dev, staging, prod)
  caddy/        Caddyfile
  scripts/      deploy, backup, restore
docs/           Documentación fuente-de-verdad
```

## Requisitos locales

- **Node 20+**
- **Python 3.12+**
- **uv** (package manager Python): `curl -LsSf https://astral.sh/uv/install.sh | sh`
- **Docker + Docker Compose**

## Arranque en dev

```bash
# 1. Levantar dependencias (Postgres, Redis, MinIO)
docker compose -f infra/compose/docker-compose.dev.yml up -d

# 2. Backend
cd apps/api
cp .env.example .env.local
uv sync
uv run alembic upgrade head
uv run uvicorn app.main:app --reload --port 8000

# 3. Frontend (otra terminal)
cd apps/web
cp .env.example .env.local
npm install
npm run dev
```

- Frontend: http://localhost:5173
- API: http://localhost:8000
- OpenAPI docs: http://localhost:8000/docs
- MinIO console: http://localhost:9001 (user: `minioadmin`, pass: `minioadmin`)

## Scripts útiles

Ver `package.json` raíz para scripts cross-workspace.

## Convenciones

- Commits: Conventional Commits (`feat:`, `fix:`, `chore:`, ...)
- Branches: `feat/...`, `fix/...`, `chore/...`
- PRs: descripción con el "por qué" + checklist (ver `docs/agents/README.md`).

## Licencia

Propietaria. Todos los derechos reservados.
