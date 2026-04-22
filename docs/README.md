# p3rDiz — Documentación

Documentación fuente-de-verdad para el ecommerce **p3rDiz – Soluciones 3D**.
Todo agente (humano o automático) que escriba código en este repositorio **debe** leer los documentos indicados antes de modificar o generar archivos.

## Cómo está organizada

```
docs/
├── README.md                          (este archivo — índice maestro)
├── brand/
│   ├── identity.md                    concepto, tono, personalidad, voz
│   └── visual-system.md               paleta, tipografías, logo, iconografía
├── product/
│   ├── product-spec.md                user stories, flujos, reglas de negocio
│   ├── roles-and-permissions.md       matriz user vs admin
│   └── customization-model.md         modelo extensible de personalizaciones
├── architecture/
│   ├── overview.md                    stack, diagrama, decisiones
│   ├── data-model.md                  entidades, ERD, archivos 3D
│   └── security.md                    JWT, OAuth, CORS, rate limiting, auditoría
├── backend/
│   ├── conventions.md                 estructura FastAPI, capas, errores, tests
│   └── api-contract.md                endpoints REST con ejemplos
├── frontend/
│   ├── conventions.md                 estructura React+TS, estado, routing, a11y
│   └── ui-components.md               sistema de componentes + tokens
├── devops/
│   ├── environments.md                envs, variables, secretos
│   ├── deployment.md                  Hetzner + Docker + Caddy + CI/CD
│   └── observability.md               Sentry, logs, uptime, backups
└── agents/
    └── README.md                      guía para agentes constructores
```

## Ruta de lectura recomendada

**Para entender el proyecto**: `brand/identity` → `product/product-spec` → `architecture/overview`.

**Para implementar backend**: `architecture/overview` → `architecture/data-model` → `architecture/security` → `backend/conventions` → `backend/api-contract`.

**Para implementar frontend**: `brand/visual-system` → `product/product-spec` → `frontend/conventions` → `frontend/ui-components` → `backend/api-contract`.

**Para desplegar o configurar infra**: `architecture/overview` → `devops/environments` → `devops/deployment` → `devops/observability`.

**Agentes automatizados**: empezar siempre por `agents/README.md`, allí se indica qué leer antes de cada tipo de tarea.

## Idioma

- Documentación y UI del producto: **español rioplatense** (uso de "vos", nunca "tú").
- Código, identificadores, commits, PRs, comentarios en código, mensajes de log: **inglés**.
- Mensajes de error visibles al usuario final: español; códigos internos de error en inglés.

## Convenciones transversales

- **Stack confirmado**: React 18 + TypeScript + Vite (frontend); FastAPI + SQLAlchemy 2 async + PostgreSQL (backend); Cloudflare R2 (archivos); Hetzner VPS + Docker Compose + Caddy (infra).
- **Moneda**: ARS en todos los precios mostrados y almacenados.
- **Timezone**: `America/Argentina/Buenos_Aires` en UI; todo timestamp en DB en UTC.
- **Monorepo**: `apps/web` (frontend), `apps/api` (backend). Directorio `packages/` reservado para código compartido (p.ej. cliente OpenAPI generado).
- **No se inventan decisiones**: si un documento no cubre un caso, el agente **debe** consultar al usuario antes de asumir.

## Estado de la documentación

Versión inicial: 2026-04-22. Esta documentación precede al código. Al empezar a implementar, cualquier desviación de lo acá escrito debe reflejarse como edición de estos docs en el mismo PR que introduce el cambio.
