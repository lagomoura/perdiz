---
name: Frontend deploy to VPS
description: Manual deploy pipeline for apps/web to the production Caddy volume
type: project
originSessionId: 909a8417-47eb-4ebb-9057-28b2654b6271
---
El frontend estático se sirve desde el named volume `aura-prod_web_dist` de Caddy en el VPS. No hay CI todavía, el deploy es manual.

**Comando canónico** (desde el repo, pwd = `apps/web/`):

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

**Why:** `VITE_API_BASE_URL` se embebe en el bundle en build time, no se lee en runtime. Si el user corre solo `npm run build`, Vite carga `.env.local` y el bundle apunta a `http://localhost:8000/v1` — no funciona en prod. Siempre construir con las vars de prod inline.

**Why volcar vía alpine:** el container de caddy monta `web_dist:/srv/web:ro`, no se puede `docker cp` ahí. El helper alpine monta el named volume en rw y copia desde `/tmp`.

**How to apply:** Cuando el usuario pida "deploy del frontend" o "actualizar la UI en prod", correr ese bloque. No commitear un `apps/web/.env.production` con la URL de DuckDNS — cuando tenga dominio definitivo habrá que actualizar la URL y el repo quedaría con referencias temporales. Tras el rebrand a Aura (2026-04-27), tanto el volumen como el dominio cambian de nombre.

**Paralelamente pendiente:** automatizar en un workflow de GitHub Actions (`deploy-prod.yml`) que haga build + rsync + docker run al push de un tag.
