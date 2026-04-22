# Arquitectura — Overview

Vista global del sistema. Decisiones y diagrama lógico. Para detalles de datos, ver `data-model.md`; para seguridad, `security.md`.

## Diagrama lógico

```
┌────────────────────┐         ┌────────────────────┐
│ Navegador (user)   │         │ Navegador (admin)  │
│ React + R3F        │         │ React admin routes │
└────────┬───────────┘         └────────┬───────────┘
         │    HTTPS                     │    HTTPS
         └──────────────┬───────────────┘
                        ▼
                 ┌─────────────┐
                 │    Caddy    │  (reverse proxy + TLS automático)
                 └──────┬──────┘
              ┌─────────┴─────────┐
              ▼                   ▼
       ┌─────────────┐     ┌─────────────┐
       │ apps/web    │     │ apps/api    │
       │ (estático)  │     │  FastAPI    │
       └─────────────┘     └──────┬──────┘
                                  │
           ┌──────────────────────┼──────────────────────┐
           ▼                      ▼                      ▼
    ┌─────────────┐        ┌─────────────┐        ┌──────────────┐
    │ PostgreSQL  │        │ Cloudflare  │        │  MercadoPago │
    │ (Docker)    │        │ R2 (S3 API) │        │  Stripe      │
    │             │        │ STL, GLB,   │        │  PayPal      │
    │             │        │ imágenes    │        │  (webhooks)  │
    └─────────────┘        └─────────────┘        └──────────────┘
           │
           ▼
    ┌─────────────┐       ┌───────────────┐
    │  pgBackups  │──→R2──│  Retención    │
    │  (diarios)  │       │  30 días      │
    └─────────────┘       └───────────────┘

Emails: Resend (HTTPS API)
Errores:  Sentry (frontend + backend)
Uptime:   Uptime Kuma (self-host mismo VPS)
```

## Stack

### Frontend (`apps/web`)

| Componente | Elección | Versión objetivo |
|---|---|---|
| Lenguaje | TypeScript | 5.x |
| Framework | React | 18.x |
| Build | Vite | 5.x |
| Estilos | TailwindCSS | 3.x |
| Componentes | shadcn/ui (Radix + Tailwind) | última |
| Formularios | react-hook-form + zod | — |
| Estado server | TanStack Query | 5.x |
| Estado client | Zustand | 4.x |
| Routing | React Router | 6.x |
| 3D preview | three.js + @react-three/fiber + @react-three/drei | última |
| HTTP client | fetch nativo envuelto + cliente OpenAPI generado | — |
| Testing | Vitest + Testing Library + Playwright | — |
| Lint/format | ESLint + Prettier | — |

### Backend (`apps/api`)

| Componente | Elección | Versión objetivo |
|---|---|---|
| Lenguaje | Python | 3.12 |
| Framework | FastAPI | 0.110+ |
| ORM | SQLAlchemy (async) | 2.x |
| Migraciones | Alembic | 1.13+ |
| Validación | Pydantic | 2.x |
| Auth | `python-jose` (JWT) + `authlib` (OAuth) | — |
| Password | `argon2-cffi` | — |
| Background jobs | **arq** (redis-based) | última |
| HTTP interno | `httpx` async | — |
| Testing | pytest + pytest-asyncio + httpx AsyncClient + testcontainers-python | — |
| Lint | ruff | — |
| Format | ruff format | — |
| Type check | mypy (strict en `app/`) | — |
| Package manager | uv | última |

### Infraestructura

| Capa | Elección |
|---|---|
| VPS | Hetzner Cloud, CPX21 (Ubuntu 24.04) |
| Orquestación | Docker Compose |
| Reverse proxy + TLS | Caddy 2 |
| DB | PostgreSQL 16 (contenedor, volumen persistente) |
| Object storage | Cloudflare R2 |
| Queue/cache | Redis 7 (contenedor, volumen persistente) |
| Email | Resend |
| Errores | Sentry (SaaS) |
| Uptime | Uptime Kuma (self-host) |
| Registro imágenes | GitHub Container Registry (GHCR) |
| CI/CD | GitHub Actions |

## Estructura del monorepo

```
/
├── apps/
│   ├── web/               React + Vite
│   └── api/               FastAPI
├── packages/
│   └── api-client/        cliente TypeScript autogenerado desde OpenAPI
├── infra/
│   ├── docker/            Dockerfiles por app
│   ├── compose/           docker-compose.prod.yml + .staging.yml
│   ├── caddy/             Caddyfile
│   └── scripts/           deploy, backup, migration bootstrap
├── docs/                  (este directorio)
├── .github/workflows/     CI + CD
├── .editorconfig
├── package.json           root con scripts del monorepo
├── pyproject.toml         shared tool config (ruff, mypy)
└── README.md
```

## Decisiones clave (ADR resumidos)

### ADR-001 — Monorepo único
**Decisión**: mantener frontend, backend y cliente generado en un solo repositorio.
**Por qué**: el equipo es pequeño, los cambios cruzan frontiera frontend/backend con frecuencia, el cliente TS generado desde el OpenAPI del backend se publica como workspace interno sin pasar por registry. Trade-off aceptado: CI corre ambos lados aunque cambie solo uno; mitigado con paths filters en GitHub Actions.

### ADR-002 — PostgreSQL como única base de datos
**Decisión**: PostgreSQL 16 para todo lo transaccional y para búsquedas.
**Por qué**: madurez, JSONB para datos semi-estructurados (personalizaciones), full-text search con diccionario español (evita dependencia inicial de ElasticSearch/Meilisearch), soporte excelente en FastAPI/SQLAlchemy. Costo cero extra al ya tener Postgres levantado.

### ADR-003 — Archivos 3D y media en Cloudflare R2
**Decisión**: STL, GLB e imágenes viven en R2; DB guarda solo metadatos y URLs.
**Por qué**: egress gratis (crítico para servir previews 3D repetidamente sin pagar por GB transferido), S3-compatible (reemplazable), tier gratis 10 GB cubre el MVP, backups cross-bucket simples.

### ADR-004 — Preview 3D con GLB (Draco)
**Decisión**: el usuario sube STL; el backend convierte a GLB comprimido con Draco; la web descarga el GLB para render; el STL original se preserva para imprimir.
**Por qué**: STL es texto o binario voluminoso; GLB+Draco es típicamente 10–30× más chico, renderiza más rápido, baja tiempo de carga en mobile. El STL sigue siendo la fuente de verdad para impresión.

### ADR-005 — JWT con refresh cookie HttpOnly
**Decisión**: access token corto (15 min) en memoria JS; refresh token rotativo (14 días) en cookie HttpOnly SameSite=Lax.
**Por qué**: balance entre ergonomía (el usuario no reloguea cada 15min) y seguridad (access no accesible desde XSS, refresh se rota en cada uso, detección de reuso revoca familia de tokens).

### ADR-006 — Queue con arq + Redis
**Decisión**: jobs de fondo (conversión STL→GLB, emails, reconciliación de pagos) corren en worker separado con arq.
**Por qué**: arq es liviano, async-nativo de Python, se monta con un contenedor más. Alternativas como Celery añaden complejidad de brokers y resultados que no necesitamos. Trade-off: arq es menos popular — mitigado por simplicidad del caso de uso.

### ADR-007 — Cliente API TypeScript generado
**Decisión**: `packages/api-client` se regenera desde el OpenAPI del backend en CI.
**Por qué**: elimina drift de tipos, autocompletado en frontend, fallos de compilación si se rompe el contrato.

### ADR-008 — Admin en misma SPA, rutas protegidas
**Decisión**: `/admin/*` vive en `apps/web` como conjunto de rutas con layout y guard propio. No se construye una SPA aparte.
**Por qué**: reutiliza el sistema de diseño, el cliente API, la build y el deploy. Los assets admin se code-splittean por ruta (lazy) para no impactar el bundle del catálogo.

### ADR-009 — Single VPS Hetzner
**Decisión**: todo corre en una VM (compose multi-container). Sin k8s, sin managed services pagos.
**Por qué**: restricción presupuestaria. El camino de escalar es separar Postgres a Hetzner Cloud DB o a una VM dedicada cuando haga falta. El diseño no asume afinidad al nodo.

## Cómo corre en dev

- `docker compose -f infra/compose/docker-compose.dev.yml up` levanta Postgres, Redis y MinIO (stand-in de R2).
- `apps/api`: `uv run uvicorn app.main:app --reload --port 8000`.
- `apps/web`: `npm run dev` (Vite, puerto 5173).
- Ver `devops/environments.md` para variables.

## Convenciones de comunicación entre capas

- Frontend nunca habla directo a Postgres ni a R2 (excepto URLs pre-firmadas que el backend emite a pedido, con TTL ≤ 10 min).
- Backend no implementa lógica de UI.
- Payments externos entran **solo** por webhooks firmados — nunca por redirects del navegador.
- Errores del backend usan códigos estables (ver `backend/conventions.md`), el frontend los traduce a mensajes en español.
- El cliente API generado es la **única** manera de llamar al backend desde el frontend; no existen `fetch` sueltos a rutas del API en código de features.
