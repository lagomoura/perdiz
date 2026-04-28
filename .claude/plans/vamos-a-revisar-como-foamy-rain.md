# Plan: Diagnosticar y arreglar deploy fallido en Vercel (con Vercel MCP)

## Contexto

El proyecto **ya está conectado a Vercel** con auto-deploy desde GitHub
(`lagomoura/criticomida_production` → `criticomida-production-qqyr`). El
último deploy `AURxwysWPJJZ6ZA8n1fi68qZiteV` está fallando y queremos:

1. Acceder a Vercel desde Claude Code para inspeccionar logs sin salir de la terminal.
2. Identificar la causa del fallo y dejar el build verde.
3. Verificar que la configuración de prod (env vars, submódulo, CORS, cookies) está sana.

Hallazgos relevantes ya verificados en el repo (`2026-04-27`):

- No existe `.vercel/` ni `vercel.json` localmente — está todo manejado por la integración GitHub de Vercel.
- `next.config.ts` tiene `eslint.ignoreDuringBuilds: false` y `typescript.ignoreBuildErrors: false`: cualquier error tipa o lint **rompe el build**.
- `.gitmodules` declara `backend/` como submódulo apuntando a `git@github.com:lagomoura/criticomida-backend.git` (SSH). Por defecto Vercel intenta inicializar submódulos en cada build → si no tiene acceso SSH al repo del backend, el build muere acá. **Es el sospechoso #1.**
- `.env` está en `.gitignore`, así que las env vars deben existir en el dashboard de Vercel. Vars usadas:
  - Públicas (cliente): `NEXT_PUBLIC_API_URL`, `NEXT_PUBLIC_GOOGLE_MAPS_API_KEY`, `NEXT_PUBLIC_SOCIAL_MOCK`.
  - Server-side (route handler `app/api/generate-category-image/route.ts`): `FAL_KEY`.
- `.env` local tiene `NEXT_PUBLIC_API_URL` **duplicado** (línea 5 = Railway, línea 14 = `localhost:8002`). Solo afecta dev local — el segundo valor gana. Cleanup separado.
- Backend en Railway: `https://criticomida-backend-production.up.railway.app/`.

## Decisiones tomadas

- **Vercel MCP**: instalar el oficial (`https://mcp.vercel.com`, OAuth) y usarlo para leer logs en lugar de tener que abrir la UI.
- **Submódulos en Vercel**: desactivarlos. `next build` no necesita `backend/` (solo se usa para `npm run test:backend`).
- **Conexión actual GitHub→Vercel**: se mantiene como está. No volvemos a linkear.

## Pasos

### 1. Instalar y autenticar Vercel MCP

Comandos a ejecutar (necesitan tu input para OAuth):

```bash
claude mcp add --transport http vercel https://mcp.vercel.com
```

Luego en la sesión de Claude Code:

```
/mcp
```

Seleccionar `vercel` → autorizar en el navegador (OAuth con tu cuenta de Vercel). Esto habilitará herramientas como buscar proyectos, listar deploys, leer build logs y runtime logs. Vercel solo permite clientes aprobados (Claude Code está aprobado).

> Nota: Yo no puedo correr `claude mcp add` por ti dentro de esta misma sesión — el comando registra MCPs en el config de Claude Code, pero los nuevos MCPs solo aparecen al reiniciar la sesión. **Workflow**: corres el comando, sales (`Ctrl-D`), reentras a Claude Code, y en la nueva sesión yo uso las herramientas Vercel MCP.

### 2. Diagnosticar el deploy fallido

Una vez autenticado, en la siguiente sesión yo:

1. Listar deploys del proyecto `criticomida-production-qqyr` y ubicar `AURxwysWPJJZ6ZA8n1fi68qZiteV`.
2. Leer build logs completos.
3. Si es un fallo de runtime (no build), traer también los runtime logs.
4. Reportar la causa raíz con el snippet exacto del error.

### 3. Hipótesis a validar primero (en orden de probabilidad)

**A. Submódulo backend no clonable** (más probable)
- Síntoma esperado en logs: `fatal: clone of 'git@github.com:lagomoura/criticomida-backend.git' into submodule path 'backend' failed`.
- Fix: Vercel Dashboard → Project Settings → Git → desactivar "Submodules" (o setear `Submodules: off`). Alternativa via env: `VERCEL_GIT_SUBMODULES=0`.

**B. Env vars públicas faltantes en Vercel**
- Síntoma esperado: build OK, runtime error en cliente al pegarle al backend (URL `localhost:8000` en bundle), o mapa de Google sin key.
- Fix: Vercel Dashboard → Project → Settings → Environment Variables. Setear para Production:
  - `NEXT_PUBLIC_API_URL=https://criticomida-backend-production.up.railway.app`
  - `NEXT_PUBLIC_GOOGLE_MAPS_API_KEY=<key>`
  - `NEXT_PUBLIC_SOCIAL_MOCK=false`
  - `FAL_KEY=<key>` (server-only, marcar como sensitive)
  - `CHAT_MODEL`, `CHAT_API_KEY` solo si los usa el frontend (en este repo solo aparecen en `.env`, no en código `app/`; probablemente sobran y son del backend — confirmar en logs).
- **Importante**: `NEXT_PUBLIC_*` se hornean en el bundle en build time. Si las agregas después de un deploy fallido, hay que **re-deployar** (no basta con guardar).

**C. Error TS o ESLint que rompe el build**
- `next.config.ts` no permite ignorar errores. Localmente probar `npm run build` para reproducir antes de tocar Vercel.

**D. Mismatch de versión de Node**
- Vercel usa Node 22 (default 2026). Next.js 15.3.8 lo soporta. Generalmente OK; revisar si el log se queja.

### 4. Plan de fix concreto (después de leer logs)

Con la causa identificada, escribiré un mini-plan secundario y lo aplicaré:

- Si es **A**: cambio de configuración en el dashboard de Vercel (paso manual tuyo, te paso el click-path) o, si prefieres, agrego un `vercel.json` con `"github": { "silent": true }` y `ignoreCommand` que evite el submódulo. La vía dashboard es más limpia.
- Si es **B**: te doy la lista exacta de envs a agregar y desde dónde sacar cada valor. Los valores los pegás vos en el dashboard (no quiero pasarlos por mi contexto).
- Si es **C**: arreglo el código que falla y commit en una nueva branch para validar el deploy preview antes de mergear a `main`.

### 5. Verificación end-to-end

Una vez verde el build:

1. Abrir `https://criticomida-production-qqyr.vercel.app` (o el dominio asignado).
2. **Smoke test**:
   - Home carga restaurantes (chequea `NEXT_PUBLIC_API_URL` está bien).
   - Mapa renderiza (chequea `NEXT_PUBLIC_GOOGLE_MAPS_API_KEY`).
   - Login funciona (chequea CORS Railway + cookies cross-domain — si falla, el backend Railway necesita `CORS_ORIGINS=https://<vercel-domain>` y `Set-Cookie: SameSite=None; Secure`).
   - Generar imagen de categoría (chequea `FAL_KEY` en server runtime).
3. Si login falla con cookies, abrir un sub-issue para ajustar el backend (no es del scope de Vercel pero rompería la app igual).

## Cleanup opcional (no bloqueante)

- `.env`: quitar la línea 14 duplicada (`NEXT_PUBLIC_API_URL=http://localhost:8002`). Es solo un foot-gun de dev local.
- `next.config.ts:57-60`: `images.remotePatterns` permite `http://localhost:8000` — innocuo en prod, lo dejaría.

## Archivos relevantes (no cambian en este plan, solo referencia)

- `/home/rtadmin/repos_personal/criticomida-nextjs/next.config.ts` — config Next.
- `/home/rtadmin/repos_personal/criticomida-nextjs/.env` — env local (no se sube).
- `/home/rtadmin/repos_personal/criticomida-nextjs/.gitmodules` — declara submódulo `backend`.
- `/home/rtadmin/repos_personal/criticomida-nextjs/app/lib/api/client.ts` — usa `NEXT_PUBLIC_API_URL` con fallback `localhost:8000`.
- `/home/rtadmin/repos_personal/criticomida-nextjs/app/api/generate-category-image/route.ts` — usa `FAL_KEY`.

## Salida esperada

- Vercel MCP autenticado en este proyecto de Claude Code.
- Causa raíz del deploy `AURxwysWPJJZ6ZA8n1fi68qZiteV` documentada con cita del log.
- Build verde en `main` con un nuevo deploy.
- App accesible en el dominio Vercel y funcional contra el backend Railway.
