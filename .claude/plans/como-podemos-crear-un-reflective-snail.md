# Dev / Prod environment split — Docker local + Railway prod

## Context

Hoy hay un único entorno mezclado:
- `criticomida-nextjs/.env` tiene `NEXT_PUBLIC_API_URL` duplicado (apunta a Railway prod **y** a `localhost:8002` en el mismo archivo — la última línea gana, frágil).
- `backend/.env` mezcla credenciales de dev con un puerto (`localhost:5433`) que sólo funciona si se corre `uvicorn` **fuera** de Docker, mientras que `.env.example` apunta a `db:5432` (modo full-docker). No queda claro cuál es el oficial.
- Railway corre el backend pero **no ejecuta migraciones** automáticamente: hay que entrar al shell y correr `alembic upgrade head` manualmente. Riesgo de olvido en cada deploy.
- No hay seed reproducible para dev: cada `docker compose up -v` deja la DB vacía y hay que correr scripts ad-hoc para tener datos de prueba.

**Objetivo:** dejar dev y prod como dos pistas paralelas que no se cruzan, con la DB de Railway de hoy clonada como snapshot inmutable que sirve de baseline para el dev local. Producción sigue su curso normal en Railway, dev arranca consistente cada vez.

**Decisiones tomadas con el usuario:**
- Seed dev = snapshot one-time de Railway prod (hoy) → restaurado en Docker local. Prod sigue intacto.
- Migraciones en Railway = automáticas en cada deploy (vía entrypoint).
- Alcance = front (Vercel) + back (Railway) + DB.

> Nota: `backend/` es submódulo (`git@github.com:lagomoura/criticomida-backend.git`). Los cambios de Dockerfile/scripts van **al repo del backend**, no al monorepo del front. El plan lo señala en cada paso.

---

## Arquitectura objetivo

```
┌─────────────────────── DEV (local) ──────────────────────┐
│  npm run dev (host)                                      │
│      │                                                   │
│      ▼  http://localhost:8002                            │
│  docker compose up  (backend/)                           │
│   ├── api      (FastAPI, --workers 2, alembic on start)  │
│   └── db       (Postgres 16, volumen pgdata persistente) │
│        ▲ snapshot one-time desde Railway prod            │
└──────────────────────────────────────────────────────────┘

┌──────────────────────── PROD ────────────────────────────┐
│  Vercel (Next.js)                                        │
│      │                                                   │
│      ▼  https://criticomida-backend-production…railway   │
│  Railway: criticomida-backend-production                 │
│   ├── service api  (Dockerfile + entrypoint con alembic) │
│   └── service postgres  (managed, separado de dev)       │
└──────────────────────────────────────────────────────────┘
```

Las dos DBs **nunca** se conectan entre sí. El único puente es el snapshot manual `pg_dump prod → restore local`, que se corre on-demand cuando dev quiere refrescarse.

---

## Cambios concretos

### 1. Snapshot one-time: Railway prod → seed local

Repo: monorepo del front (los scripts viven en `backend/`, pero esto es operación, no código).

- Obtener `DATABASE_URL` pública de Railway (Railway → Postgres service → Connect → Public Network).
- Ejecutar (una vez, hoy):
  ```bash
  pg_dump --no-owner --no-acl --format=custom \
    "<RAILWAY_PUBLIC_DATABASE_URL>" \
    > backend/scripts/seeds/dev_baseline.dump
  ```
- Guardar el dump como `backend/scripts/seeds/dev_baseline.dump`.
- Agregar `scripts/seeds/*.dump` a `backend/.gitignore` (el archivo es grande y contiene datos reales — no se commitea; se distribuye por canal seguro, ej. Drive privado).
- Documentar el comando de refresh en `backend/README.md` para futuras actualizaciones del baseline.

### 2. Script de restore para dev (nuevo)

Archivo nuevo en repo backend: `backend/scripts/restore_dev_db.sh`

```bash
#!/bin/sh
set -e
DUMP="${DUMP:-scripts/seeds/dev_baseline.dump}"
docker compose exec -T db pg_restore \
  --clean --if-exists --no-owner --no-acl \
  -U "${POSTGRES_USER:-criticomida}" \
  -d "${POSTGRES_DB:-criticomida}" \
  < "$DUMP"
echo "Dev DB restored from $DUMP"
```

Uso:
```bash
cd backend
docker compose up -d db
./scripts/restore_dev_db.sh
docker compose up api
```

### 3. Entrypoint del backend: migraciones auto en deploy

Archivo nuevo en repo backend: `backend/entrypoint.sh`

```sh
#!/bin/sh
set -e
echo "Running alembic upgrade head..."
alembic upgrade head
echo "Starting uvicorn on port ${PORT:-8000}"
exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}" --workers 2
```

Modificar `backend/Dockerfile` (cambia las últimas líneas):
```dockerfile
COPY . .
RUN chmod +x entrypoint.sh
EXPOSE 8000
CMD ["./entrypoint.sh"]
```

Beneficios:
- Railway corre `alembic upgrade head` antes de levantar la API en cada deploy.
- Si la migración falla, el contenedor no arranca → Railway muestra el error claro en logs.
- Dev local hereda lo mismo (al hacer `docker compose up api`), así nunca hay drift entre lo que hace el dev y lo que hace prod.
- `${PORT:-8000}` respeta la variable que Railway inyecta automáticamente.

### 4. Variables de entorno — backend

**Local dev** (`backend/.env`, gitignored, modo full-docker):
```
DATABASE_URL=postgresql+asyncpg://criticomida:criticomida_secret@db:5432/criticomida
POSTGRES_USER=criticomida
POSTGRES_PASSWORD=criticomida_secret
POSTGRES_DB=criticomida
JWT_SECRET=<dev-secret-cualquiera>
APP_ENV=development
COOKIE_SECURE=false
CORS_ORIGINS=http://localhost:3000
CHAT_MODEL=gemini/gemini-2.5-flash
CHAT_API_KEY=<dev key, OK reciclar la actual>
GOOGLE_PLACES_API_KEY=<dev key>
FAL_KEY=<dev key>
```

**Acción:** alinear `backend/.env` actual al modo `db:5432` (que es el que asume `docker-compose.yml`). Si quieres seguir corriendo `uvicorn` fuera de Docker en algún caso, mantenemos un `backend/.env.host` separado con `localhost:5433`.

**Producción** (Railway UI, no archivo):
```
DATABASE_URL=<auto-inyectada por el servicio Postgres de Railway>
JWT_SECRET=<openssl rand -hex 32, distinto al de dev>
APP_ENV=production
COOKIE_SECURE=true
CORS_ORIGINS=https://<vercel-app>.vercel.app
CHAT_MODEL, CHAT_API_KEY, GOOGLE_PLACES_API_KEY, FAL_KEY=<keys de prod>
PORT=<auto-inyectada>
```

Actualizar `backend/.env.example` para reflejar la versión "full-docker" como canónica y agregar comentarios sobre el modo Railway.

### 5. Variables de entorno — frontend

Archivos en el monorepo del front:

- `.env.development` (committed, sin secretos):
  ```
  NEXT_PUBLIC_API_URL=http://localhost:8002
  NEXT_PUBLIC_SOCIAL_MOCK=true
  ```
- `.env.development.local` (gitignored, claves de browser que el dev necesita):
  ```
  NEXT_PUBLIC_GOOGLE_MAPS_API_KEY=<key>
  FAL_KEY=<key si server-side actions del front lo usan>
  CHAT_MODEL=gemini/gemini-2.5-flash
  CHAT_API_KEY=<key>
  ```
- `.env` actual: limpiar el `NEXT_PUBLIC_API_URL` duplicado y eventualmente borrar el archivo (Next.js carga `.env.development` automático con `npm run dev`).
- Vercel UI (Production environment): `NEXT_PUBLIC_API_URL=https://criticomida-backend-production.up.railway.app`, más `NEXT_PUBLIC_GOOGLE_MAPS_API_KEY` y cualquier otra `NEXT_PUBLIC_*` necesaria. Vercel **no** lee archivos `.env.production` del repo — todo va por la UI o `vercel env`.

Verificar `.gitignore` del front:
```
.env*.local
.env
```
(Probablemente ya está, hay que confirmar.)

### 6. Documentación

Actualizar `criticomida-nextjs/CLAUDE.md` agregando una sección **"Dev vs Prod"** corta:
- Cómo arrancar dev (3 comandos).
- Cómo refrescar el baseline desde prod (cuándo y cómo).
- Cómo se hacen los deploys (push → Vercel + Railway auto-deploy; alembic corre en el entrypoint).
- Tabla de variables por entorno.

### 7. Higiene de secretos (importante)

Las llaves actuales de `backend/.env` (`FAL_KEY`, `GOOGLE_PLACES_API_KEY`, `CHAT_API_KEY`) son visibles en disco. Verificar que **nunca** estuvieron en git history del backend (`git log --all -p -- .env`). Si lo estuvieron, rotarlas. Si no, se pueden seguir usando como dev keys, pero **prod debe usar keys distintas** seteadas sólo en Railway.

---

## Archivos a modificar

| Archivo | Repo | Cambio |
|---|---|---|
| `backend/Dockerfile` | backend | CMD → entrypoint.sh |
| `backend/entrypoint.sh` | backend | nuevo, runs alembic + uvicorn |
| `backend/scripts/restore_dev_db.sh` | backend | nuevo |
| `backend/scripts/seeds/.gitkeep` | backend | nuevo (carpeta) |
| `backend/.gitignore` | backend | agregar `scripts/seeds/*.dump` |
| `backend/.env.example` | backend | usar `db:5432`, comentar modos |
| `backend/.env` | local | ajustar a `db:5432` |
| `criticomida-nextjs/.env.development` | front | nuevo, committed |
| `criticomida-nextjs/.env.development.local` | front | nuevo, gitignored |
| `criticomida-nextjs/.env` | front | borrar (Next.js usa los `.env.development`) |
| `criticomida-nextjs/.gitignore` | front | confirmar `.env*.local` y `.env` |
| `criticomida-nextjs/CLAUDE.md` | front | sección Dev vs Prod |
| Vercel UI | — | env vars de prod |
| Railway UI | — | env vars de prod (incluir `JWT_SECRET` rotado) |

Reutilizamos:
- `backend/docker-compose.yml` — ya está bien (port mapping `8002:8000`, healthcheck, volumen pgdata).
- `backend/alembic/` — sin cambios; el entrypoint lo invoca.
- `backend/scripts/*` — los scripts de import existentes quedan disponibles para casos puntuales (no se usan para el seed cotidiano).

---

## Verificación end-to-end

**Dev local — fresh start:**
```bash
cd backend
docker compose down -v                 # wipe pgdata
docker compose up -d db                # arranca DB sola
./scripts/restore_dev_db.sh            # carga snapshot
docker compose up api                  # debería correr alembic upgrade head y arrancar
# en otra terminal, desde el monorepo:
cd ..
npm run dev
# abrir http://localhost:3000 → ver datos del snapshot (83 restaurantes, etc.)
```

Checklist:
- [ ] `docker compose logs api` muestra `Running alembic upgrade head` antes de uvicorn.
- [ ] `curl http://localhost:8002/restaurants?limit=1` devuelve un restaurante real del snapshot.
- [ ] Frontend muestra los datos esperados (no fallback de `app/data/`).

**Prod — verificar auto-migración:**
- Crear una migración trivial en backend (`alembic revision -m "noop"` con un `pass`).
- Push al repo backend → Railway auto-deploy.
- Revisar logs de Railway: deben mostrar `alembic upgrade head` corriendo y `Starting uvicorn` después.
- Hacer rollback de la migración trivial.

**Aislamiento dev/prod:**
- Conectarse a la DB local (`psql ... localhost:5433`) y crear un registro dummy.
- Confirmar que **no** aparece en prod (consultando la API de Railway).
