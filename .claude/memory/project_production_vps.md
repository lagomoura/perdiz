---
name: Production VPS (Hetzner)
description: Deployment target, domain, paths, users, and what runs where in production
type: project
originSessionId: 909a8417-47eb-4ebb-9057-28b2654b6271
---
Backend de producción live en Hetzner CPX21, IP `116.203.202.6`, Ubuntu 24.04. Dominio temporal DuckDNS: `aura3d.duckdns.org` (wildcard). Antes era `p3rdiz.duckdns.org`; el rebrand a Aura fue el 2026-04-27.

**URLs públicas:**
- API: `https://api.aura3d.duckdns.org` (TLS via Let's Encrypt por Caddy)
- Frontend (futuro): `https://aura3d.duckdns.org`
- Uptime Kuma: `https://uptime.aura3d.duckdns.org` (basic auth `admin` / password en password manager)

**VPS layout:**
- Usuario `deploy` con sudo sin password, en grupo docker. Root login + password auth deshabilitados en sshd.
- Repo en `/opt/aura` (clonado desde github.com/lagomoura/perdiz, público — el repo conserva el nombre viejo en GitHub).
- Compose en `/opt/aura/infra/compose/docker-compose.prod.yml` (build-on-VPS, imagen tag `aura-api:local`, project name `aura-prod`).
- `.env.production` y `.env.production.postgres` en `/opt/aura/` (chmod 600, fuera del repo).
- `.env` con `AURA_DOMAIN` y `UPTIME_BASIC_AUTH_HASH` en `/opt/aura/infra/compose/` (auto-cargado por compose).
- DB Postgres: usuario `aura`, db `aura` (renombrada desde `perdiz` durante el rebrand).
- UFW activo: 22/80/443.

**Pendiente de configurar en `.env.production`:** R2 (uploads), MercadoPago (pagos), Resend (emails), Sentry, bootstrap admin, OAuth. Features correspondientes fallan hasta que se carguen. Post-rebrand: bucket R2 puede llamarse `aura-media-prod` o seguir con `perdiz-media-prod` durante la migración.

**Aún no desplegado:** frontend estático (volumen `web_dist` vacío), CI/CD (no hay workflow `deploy-prod.yml`), backups a R2, fail2ban.

**Why:** MVP barato single-node. Build local evita depender de GHCR hasta tener CI/CD real. DuckDNS hasta comprar dominio definitivo.

**How to apply:** Cuando el usuario pregunte por estado de producción, URLs de API para testing, o variables de entorno disponibles, consultá esta nota primero. Antes de tocar el VPS, recordá que los cambios al compose/Dockerfile hechos localmente ya están aplicados vía scp sin commitear todavía — verificá `git status` para no duplicar. Tras el rebrand, el path `/opt/perdiz` ya no existe en el VPS hasta que se ejecute la Fase 3 del plan de migración.
