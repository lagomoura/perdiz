# Observabilidad — Aura

Qué medir, cómo alertar, qué hacer ante incidentes.

## Principios

- **Todo error que no se ve no existe**: errores llegan a Sentry en tiempo real.
- **Logs estructurados**: stdout JSON en todos los contenedores. Nunca imprimir secretos.
- **Métricas cuando haga falta**: el MVP **no** monta Prometheus/Grafana. Se suma si los KPIs o el debugging lo requieren.
- **Una sola fuente de alertas**: para no dispersar, Uptime Kuma y Sentry concentran notificaciones al email admin.

## Sentry

Dos proyectos:

- `aura-api` (backend) — `SENTRY_DSN` en env backend.
- `aura-web` (frontend) — `VITE_SENTRY_DSN` en env frontend.

### Configuración backend

- `sentry_sdk.init(..., traces_sample_rate=0.1, profiles_sample_rate=0.0)` en prod.
- Integraciones: FastAPI, SQLAlchemy, Redis.
- Scrubbing de `password`, `token`, `secret`, `authorization`, `cookie` (hook `before_send`).
- `release` taggeado con el SHA del deploy.
- `environment` = `APP_ENV`.

### Configuración frontend

- `@sentry/react` + `BrowserTracing` con `tracesSampleRate: 0.1`.
- `Sentry.ErrorBoundary` envuelve el árbol.
- Errores de red (fetch fallidos, 5xx) se reportan con `beforeSend` filtro de 4xx esperados.

### Alertas Sentry

- **Issue nuevo** (error no visto antes) → email inmediato.
- **Tasa de errores** supera 10 eventos/5min → email.
- **Spike** detectado por algoritmo de Sentry → email.

## Logs

- **Formato JSON** con structlog (backend) y consola estructurada (frontend para debug local; el frontend manda errores a Sentry, no logs).
- **Campos mínimos por evento**:
  - `timestamp` (UTC ISO)
  - `level` (`INFO`/`WARN`/`ERROR`/`DEBUG`)
  - `message`
  - `request_id` (si aplica)
  - `user_id` (si aplica)
  - `path`, `method`, `status`, `duration_ms` para request logs
  - `error.type`, `error.message` para errores
- **Retención**: `docker logs` tiene rotación por size (`max-size=20m`, `max-file=5`). Si se necesita más histórico, sumar Loki como fase posterior.

## Uptime Kuma

Self-hosted en el mismo VPS (contenedor), accesible en `uptime.aura.ar` con basic auth.

Monitores configurados:
- `GET https://aura.ar` cada 60s.
- `GET https://api.aura.ar/health` cada 30s.
- `GET https://api.aura.ar/health/deep` cada 5 min.
- TLS expiry de `aura.ar`, `api.aura.ar`.
- DNS NS consistency.

Notificaciones: email admin + (futuro) Telegram bot.

## Health endpoints

### `GET /health`
Responde 200 con `{ "status": "ok" }`. No chequea dependencias. Objetivo: saber si el proceso está vivo.

### `GET /health/deep`
Chequea:
- `SELECT 1` a Postgres.
- `PING` a Redis.
- `HEAD` a R2 (objeto conocido, con TTL de cache 30s para no martillar).

Responde:
```json
{
  "status": "ok" | "degraded",
  "checks": {
    "postgres": "ok" | "fail",
    "redis": "ok" | "fail",
    "r2": "ok" | "fail"
  }
}
```
`degraded` → status 503.

## Trace IDs

Middleware backend genera un `request_id` (ULID) por cada request entrante (o respeta uno entrante si viene con header `X-Request-ID`). Se:
- Agrega a todos los logs.
- Envía de vuelta en header `X-Request-ID`.
- Frontend puede mostrarlo en errores ("código de referencia: 01HW...") para facilitar soporte.

## Métricas que importan (monitoreo informal)

Aunque no haya Prometheus, revisar periódicamente:
- **Latencia p95 de requests** — visible en Sentry Performance (con `traces_sample_rate` configurado).
- **Errores 5xx / min** — Sentry.
- **Duración de jobs arq** (conversión STL→GLB, envío de emails) — log de inicio/fin de cada job con `duration_ms`.
- **Pedidos atascados** en `pending_payment` > 2h → job diario que los marca para revisión.
- **Uso de disco** en VPS — alerta del propio Hetzner o cron simple que avisa >75%.
- **Egresos R2** — dashboard de Cloudflare.
- **Envíos Resend** — dashboard de Resend (bounces, quejas).

## Dashboard admin como observabilidad del negocio

Los KPIs visibles al admin cubren la capa de negocio:
- Pedidos por estado.
- Revenue del período.
- Top productos.
- Nuevos usuarios.

No reemplaza la observabilidad técnica; son planos distintos.

## Runbook mínimo

Ante errores escalados:

1. **Servicio caído (Uptime Kuma notifica)**:
   - SSH al VPS.
   - `docker compose ps` → ver estado de contenedores.
   - `docker compose logs --tail=200 <servicio>` → revisar últimos logs.
   - Si rollback de código: ver `devops/deployment.md` § rollback.

2. **Spike de errores en Sentry**:
   - Abrir Sentry, filtrar por release.
   - Si correlaciona con deploy reciente: rollback.
   - Si correlaciona con dependencia externa (pasarela, R2): chequear status page del proveedor.

3. **Pagos no se confirman**:
   - Revisar logs del endpoint de webhook (`logger.bind(webhook_provider='mercadopago')`).
   - Confirmar que el webhook URL está registrado en el panel del proveedor.
   - Si es ventana corta: job `reconcile_payment` barre pedidos `pending_payment` con pago aprobado en provider.

4. **Usuario no recibe email**:
   - Dashboard de Resend → buscar por dirección.
   - Si bounce: revisar si el email fue tipeado mal; si catch-all/spam: pedir al usuario chequear; si nada, hotmail/outlook a veces atrasan (30 min ok).

## Privacidad y compliance

- El usuario puede solicitar exportación o borrado de sus datos. No está en MVP, pero los logs y la PII están acotados y etiquetados para facilitar cumplimiento futuro.
- No se exportan PII a terceros salvo: pasarela (nombre + email para pago), Resend (email para enviar), Sentry (scrubbed).
