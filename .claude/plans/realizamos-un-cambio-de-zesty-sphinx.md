# Rebrand p3rDiz → Aura

## Context

El proyecto cambia de identidad: pasa a llamarse **Aura** (antes `p3rDiz`) con el descriptor **Impresiones 3D** (antes `Soluciones 3D`). Hay un logo nuevo en `source/aura_logo.png` con paleta rojo-anaranjada + amarillo sobre grafito. El usuario eligió:

- Nuevo subdominio temporal DuckDNS: **`aura3d.duckdns.org`** (reemplaza `p3rdiz.duckdns.org`).
- **Rebrand completo**, incluyendo runtime/prod: DB, buckets, paths, containers, env vars.
- **Logo PNG** + favicon derivado (ICO/SVG) para nitidez en pestaña del navegador.
- **Tunear paleta** hacia los tonos del logo Aura (rojo-naranja ~`#E94E1B` + acento amarillo ~`#F4B41A`).

El alcance toca el repo, el VPS productivo (Hetzner `116.203.202.6`, layout `/opt/perdiz/`, DB `perdiz`, bucket `perdiz-media`, containers `perdiz-prod-*`) y DuckDNS. Es alto riesgo: requiere downtime, dump/restore de Postgres y posible re-bootstrap parcial del VPS.

---

## Pre-requisitos (acciones del usuario, antes de empezar)

1. **Registrar `aura3d` en duckdns.org** apuntando a `116.203.202.6` (cuenta del usuario, no automatizable desde aquí).
2. **Backup completo del VPS** antes de tocar nada:
   - `pg_dump` de la DB `perdiz` (lo hace `infra/scripts/backup.sh` o manual).
   - Snapshot del directorio `/opt/perdiz/.env.production*` (los secrets no están en el repo).
   - Si R2 ya tiene archivos en `perdiz-media-prod`, listar el contenido — para decidir si renombrar el bucket o redirigir a uno nuevo.
3. **Confirmar ventana de downtime** (estimado 15–30 min para la migración de prod).

---

## Fase 1 — Rebrand en código (repo, bajo riesgo)

### 1.1 Identidad visual y display strings

**Logo (PNG + favicon)**:
- Copiar `source/aura_logo.png` → `apps/web/public/brand/logo.png`.
- Generar `apps/web/public/brand/favicon.ico` (32×32) + `favicon-180.png` (apple-touch). Herramienta: `convert` (ImageMagick) o un servicio offline.
- (Opcional) eliminar el viejo `apps/web/public/brand/logo.svg` una vez confirmado el render.
- `apps/web/index.html:5` — cambiar `<link rel="icon">` a `favicon.ico` + agregar `apple-touch-icon`.
- `apps/web/index.html:7` — `theme-color` al nuevo naranja (ver §1.2).
- `apps/web/index.html:8` — `<title>Aura — Impresiones 3D</title>`.
- `apps/web/src/components/ui/Logo.tsx:10-11` — `src="/brand/logo.png"`, `alt="Aura — Impresiones 3D"`.

**Textos visibles**:
- `apps/web/src/locales/es.json:61` — `"subtitle": "Impresiones 3D con precisión técnica y alma creativa."`
- `README.md:1` — `# Aura — Impresiones 3D`.
- `docs/README.md:3` — `Aura – Impresiones 3D`.

### 1.2 Paleta de colores (tunear a tonos Aura)

`apps/web/src/styles/tokens.css`:
- `--brand-orange-500: 233 78 27`  (`#E94E1B`, rojo-naranja del logo)
- `--brand-orange-600: 196 60 18`  (`#C43C12`, hover)
- `--brand-orange-100: 253 224 211` (soft)
- Agregar acento amarillo: `--brand-amber-500: 244 180 26` (`#F4B41A`)
- `--shadow-focus`: actualizar al nuevo `rgb(233 78 27 / 0.35)`

`apps/web/tailwind.config.ts:8-17` — agregar mapeo `amber` paralelo al `orange`.

`apps/web/index.html:7` — `<meta name="theme-color" content="#E94E1B" />`.

**Verificación de contraste**: tras el cambio, abrir el sitio dev y revisar botones primarios, links activos, focus rings y estados hover. WCAG AA (contraste ≥ 4.5:1) sobre blanco.

### 1.3 Package identifiers (cosmético, no afecta runtime)

- `package.json:2` → `"name": "aura"`.
- `apps/web/package.json:2` → `"name": "@aura/web"`.
- `apps/api/pyproject.toml:2` → `name = "aura-api"`.
- `packages/api-client/package.json:2` → `"name": "@aura/api-client"`.
- `packages/api-client/README.md:1` → `# @aura/api-client`.

Tras renombrar paquetes JS: re-ejecutar `npm install` en raíz para que el lockfile se actualice. Verificar imports `@perdiz/...` en el código (con grep) y migrarlos a `@aura/...`.

### 1.4 Documentación de marca

- `docs/brand/identity.md` — reescribir nombre, tagline, story (mantener voz/tono).
- `docs/brand/visual-system.md` — reescribir descripción del logo (sin perdiz isotipo; ahora es la "A" con boquilla 3D), descriptor "IMPRESIONES 3D", colores nuevos.
- `docs/architecture/data-model.md:463` — `site.name` default → `'Aura'`.
- `docs/backend/api-contract.md` — actualizar título y ejemplos (`Llavero low-poly perdiz` → ejemplo neutro tipo `Llavero personalizado`).
- `docs/frontend/ui-components.md` — buscar/reemplazar menciones de p3rDiz.
- `docs/devops/environments.md`, `deployment.md`, `observability.md` — actualizar dominios y nombres de proyectos Sentry (ver Fase 4).
- `apps/api/.env.example` y `apps/api/.env.local` líneas 1-2, 56-57, 65 — `EMAIL_FROM=Aura <hola@aura.local>`, `EMAIL_SUPPORT=soporte@aura.local`, `BOOTSTRAP_ADMIN_EMAIL=admin@aura.local`.
- `apps/api/app/config.py:71-72` — defaults de `email_from` / `email_support` a Aura.
- `apps/web/.env.example:1` — comentario header.

### 1.5 Test fixtures (cosmético)

`apps/api/tests/integration/test_stl_to_glb.py:22`, `test_user_uploads.py:32`, `test_admin_uploads.py:51` — header `b"aura test stl"` (no afecta lógica, sólo el header del binario STL fake).

---

## Fase 2 — Rebrand de identificadores runtime (repo)

Estos cambios tocan nombres que el VPS también usa. **Coordinar con Fase 4** (los cambios en el repo y en prod deben aplicarse juntos en el mismo deploy).

### 2.1 Variable de entorno de dominio

`PERDIZ_DOMAIN` → `AURA_DOMAIN` en:
- `infra/caddy/Caddyfile:4,18,23`
- `infra/compose/docker-compose.prod.yml:11`
- `infra/scripts/deploy.sh:17`
- Cualquier doc en `docs/devops/` que la mencione.

Default fallback: `aura.local` (en lugar de `perdiz.local`).

### 2.2 Nombres de containers/proyectos Compose

- `infra/compose/docker-compose.dev.yml:1` → `name: aura-dev`
- `infra/compose/docker-compose.prod.yml:1` → `name: aura-prod`
- `infra/compose/docker-compose.prod.yml:24,38` — image tags `aura-api:local`
- `infra/compose/docker-compose.prod.yml:26,40,49` — `env_file: /opt/aura/.env.production*`
- `infra/scripts/backup.sh:13` → `docker exec aura-prod-postgres-1 pg_dump -U aura aura`
- `infra/scripts/backup.sh:10` → prefijo `aura_`
- `infra/scripts/deploy.sh:2` → comentario `/opt/aura`

### 2.3 DB credenciales (desarrollo) y buckets

- `infra/compose/docker-compose.dev.yml:8-10,16` — `POSTGRES_DB/USER/PASSWORD: aura`. Como dev es desechable, vale recrear el volumen `pgdata` en local. Documentar en el commit que requiere `docker compose down -v`.
- `infra/compose/docker-compose.dev.yml:61-63` — buckets MinIO `aura-media`, `aura-media-private`.
- `apps/api/.env.example` y `.env.local` líneas 15, 40, 41 — DB URL y `R2_BUCKET=aura-media`, `R2_PUBLIC_BASE_URL` con `aura-media`.
- `infra/docker/web.Dockerfile:11` — `VITE_API_BASE_URL=https://api.aura.local/v1`.

### 2.4 Sentry / JWT

`docs/devops/observability.md:16-17` — los proyectos en Sentry serán `aura-api` y `aura-web`. **El usuario debe crear los proyectos nuevos en Sentry y obtener nuevos DSNs**, o renombrar los existentes (Sentry permite rename, los DSN no cambian). Documentar la decisión.

`docs/architecture/security.md:11` — JWT `iss=aura-api`, `aud=aura-web`. Cambiar el default en `apps/api/app/config.py` y agregar nota de migración: tokens emitidos antes del cambio dejarán de validarse. Aceptable porque los users tendrán que volver a loguearse — alternativa es soportar ambos `iss` durante 7 días.

---

## Fase 3 — Cambios en el VPS productivo (alto riesgo)

Ejecutar en este orden, con `deploy@116.203.202.6`:

### 3.1 Backup pre-migración

```bash
# Como deploy en el VPS
cd /opt/perdiz
docker compose -f infra/compose/docker-compose.prod.yml exec -T postgres \
  pg_dump -Fc -U perdiz perdiz > /tmp/perdiz_pre_aura_$(date +%F).dump
sudo cp -a /opt/perdiz/.env.production* /opt/perdiz_envs_backup_$(date +%F)/
```

Bajar copia local con `scp`.

### 3.2 Renombrar DB postgres (in-place o dump/restore)

**Opción dump/restore** (más limpia, requiere container nuevo):

```bash
docker compose -f infra/compose/docker-compose.prod.yml down
# Editar /opt/perdiz/.env.production.postgres: POSTGRES_DB=aura, POSTGRES_USER=aura
# Renombrar volume: docker volume create perdiz_pgdata_old; recrear vacío
# Restore con pg_restore --no-owner --role=aura desde el dump renombrado
```

**Opción ALTER en-vivo** (más rápida, sin recrear volume):

```sql
-- Conectar como superuser, sin conexiones activas a perdiz
ALTER DATABASE perdiz RENAME TO aura;
ALTER USER perdiz RENAME TO aura;
ALTER ROLE aura WITH PASSWORD '<nuevo o el mismo>';
```

Recomendación: **dump/restore**, porque también rota credenciales y deja un punto de retorno claro. Implica mover el path del compose a `/opt/aura/`.

### 3.3 Renombrar `/opt/perdiz/` → `/opt/aura/`

```bash
sudo systemctl stop docker  # o `docker compose down` solamente
sudo mv /opt/perdiz /opt/aura
# Editar /opt/aura/.env (cambiar PERDIZ_DOMAIN -> AURA_DOMAIN=aura3d.duckdns.org)
# Editar /opt/aura/.env.production (R2_BUCKET=aura-media-prod si renombramos bucket)
git -C /opt/aura pull origin main  # con los cambios de Fase 1+2 ya mergeados
docker compose -f infra/compose/docker-compose.prod.yml build
docker compose -f infra/compose/docker-compose.prod.yml up -d
```

### 3.4 R2 (Cloudflare)

- Crear bucket nuevo `aura-media-prod` en Cloudflare R2.
- Copiar contenido de `perdiz-media-prod` a `aura-media-prod` con `rclone copy r2:perdiz-media-prod r2:aura-media-prod` (requiere `rclone` configurado; si no, dejarlo para Fase 5 y mantener el bucket viejo apuntado por `R2_BUCKET=perdiz-media-prod` durante un tiempo).
- Actualizar `.env.production` con `R2_BUCKET=aura-media-prod` y `R2_PUBLIC_BASE_URL` correspondiente.
- Si hay un CNAME `media.perdiz.ar` o similar, recrearlo apuntando al bucket nuevo.

---

## Fase 4 — DNS + TLS (DuckDNS + Caddy)

1. Confirmar que `aura3d.duckdns.org` resuelve a `116.203.202.6` (`dig aura3d.duckdns.org`).
2. En `/opt/aura/infra/compose/.env`: `AURA_DOMAIN=aura3d.duckdns.org`.
3. `docker compose -f infra/compose/docker-compose.prod.yml restart caddy` para que Caddy emita certs Let's Encrypt para los tres hosts: `aura3d.duckdns.org`, `api.aura3d.duckdns.org`, `uptime.aura3d.duckdns.org`.
4. Verificar TLS con `curl -fsS https://api.aura3d.duckdns.org/health`.
5. Mantener `p3rdiz.duckdns.org` apuntando a la misma IP por unos días como fallback (DuckDNS permite múltiples subdominios), sin servirlo desde Caddy.

---

## Fase 5 — Verificación end-to-end

**Local (después de Fase 1+2)**:
- `cd apps/web && npm run dev` — abrir, ver logo Aura, título de pestaña, favicon, paleta nueva, tagline "Impresiones 3D".
- `cd apps/api && uv run pytest` — los tests pasan con nuevo header.
- `ruff format --check .` desde `apps/api/` (CI check).
- `npm run build` en `apps/web` — sin warnings de assets faltantes.

**Producción (después de Fase 3+4)**:
- `curl -fsS https://api.aura3d.duckdns.org/health` → `200 OK`.
- Frontend (cuando esté desplegado): cargar `https://aura3d.duckdns.org`, ver logo + tagline + favicon.
- DB: `docker exec aura-prod-postgres-1 psql -U aura -d aura -c '\dt'` muestra las tablas.
- R2: subir un asset de prueba desde el panel admin, comprobar que se sirve desde `aura-media-prod`.
- Sentry: forzar un error de prueba y verificar que llega al proyecto Aura.

---

## Fase 6 — Cleanup post-rebrand

- Eliminar `apps/web/public/brand/logo.svg` viejo si todavía está.
- Borrar `source/aura_logo.png` del repo si ya está copiado a `public/brand/` (o moverlo a `docs/brand/source/`).
- Después de 7 días sin issues: borrar `perdiz-media-prod` (R2), `p3rdiz.duckdns.org`, dump pre-migración.

---

## Archivos críticos a modificar

**Frontend**:
- `apps/web/index.html`, `apps/web/src/components/ui/Logo.tsx`, `apps/web/src/locales/es.json`, `apps/web/src/styles/tokens.css`, `apps/web/tailwind.config.ts`, `apps/web/public/brand/*`, `apps/web/.env.example`, `apps/web/package.json`.

**Backend**:
- `apps/api/.env.example`, `apps/api/.env.local`, `apps/api/app/config.py`, `apps/api/pyproject.toml`, tests (3 archivos en `tests/integration/`).

**Infra**:
- `infra/caddy/Caddyfile`, `infra/compose/docker-compose.prod.yml`, `infra/compose/docker-compose.dev.yml`, `infra/scripts/deploy.sh`, `infra/scripts/backup.sh`, `infra/docker/web.Dockerfile`.

**Repo root y packages**:
- `package.json`, `README.md`, `docs/README.md`, `docs/brand/*.md`, `docs/architecture/*.md`, `docs/backend/api-contract.md`, `docs/devops/*.md`, `docs/frontend/ui-components.md`, `packages/api-client/package.json`, `packages/api-client/README.md`.

---

## Memoria persistente a actualizar

Después de aplicar, actualizar:
- `~/.claude/projects/-home-rtadmin-repos-personal-perdiz/memory/project_production_vps.md` — nuevo dominio, nuevo path `/opt/aura/`, DB `aura`, container names.
- `~/.claude/projects/-home-rtadmin-repos-personal-perdiz/memory/project_web_deploy.md` — nuevos `VITE_API_BASE_URL`, dominios, paths.
- `~/.claude/projects/-home-rtadmin-repos-personal-perdiz/memory/MEMORY.md` — renombrar entradas si conviene (opcional).

---

## Riesgos y mitigaciones

| Riesgo | Mitigación |
|---|---|
| DB rename rompe migrations futuras | Dump/restore + verificar `alembic current` post-migración |
| R2 bucket nuevo vacío sin migrar archivos | Mantener bucket viejo accesible hasta validar copia con `rclone` |
| JWT tokens viejos invalidados por cambio `iss/aud` | Aceptar logout global, comunicar; o doble-iss durante 7 días |
| Caddy no emite cert para nuevo dominio | Confirmar que el subdominio resuelve antes de levantar Caddy; mirar logs `docker logs aura-prod-caddy-1` |
| Volumen `perdiz_pgdata` huérfano queda ocupando disco | Borrar `docker volume rm perdiz_pgdata` recién después de validar la migración |
| Memoria stale referenciando p3rdiz/duckdns viejo | Actualizar archivos de memory en la misma sesión post-deploy |

---

## Estrategia de commits / PRs sugerida

Dado que es un cambio grande pero coherente, **un solo PR con varios commits ordenados** es razonable:

1. `chore: rename package identifiers perdiz → aura`
2. `feat(web): replace logo asset and tune brand palette to Aura`
3. `feat(web): update display strings and tagline (Impresiones 3D)`
4. `chore(infra): rename PERDIZ_DOMAIN env, compose project, container names`
5. `chore(infra): switch DB credentials and R2 bucket defaults to aura`
6. `docs: rebrand identity, visual-system, and devops docs`

VPS migration (Fase 3+4) corre **después** del merge a `main`, manualmente como deploy.
