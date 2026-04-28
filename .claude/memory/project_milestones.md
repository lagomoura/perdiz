---
name: Project milestones shipped
description: Running record of what's complete in main so session resumes don't have to rederive the state
type: project
originSessionId: e4a21e96-1b5e-470a-af8a-cc20daf612e6
---
## Backend — MILESTONE A COMPLETO (abr 2026)

PRs mergeados a main:
- #1 auth backend (email/pass, JWT + refresh rotativo con reuse detection)
- #2 auth frontend (login, registro, verificación, mi-cuenta)
- #3 catalog models (categorías, productos, media_files, customization, discounts)
- #4 catalog public endpoints (GET /categories, /products + FTS + filtros + cursor)
- #5 admin catalog core (audit_log + CRUD categorías + CRUD productos + transitions)
- #6 admin customizations + product_images metadata + volume/automatic discounts CRUD
- #7 admin uploads presign+commit (image + model_stl) contra R2/MinIO
- #8 STL→GLB conversion async con arq + auto-schedule en admin STL commit
- #9 fix CI MinIO
- #10 user uploads (verified user + rate limit) + cleanup cron diario
- #11 user cart + admin coupons CRUD (carrito + customizaciones + pricing con stacking)
- #12 checkout + orders + MercadoPago sandbox + webhook
- #13 fix ruff format migración 0005
- #14 user order history + admin orders ops (state machine + refund + notes) + transactional emails stub

**Why:** Milestone A terminado con MercadoPago only (decisión explícita del 2026-04-23). Stripe + PayPal quedan **fuera de scope** del MVP — no agregar sin re-confirmación del usuario.

**How to apply:** Antes de planear features backend, revisar si ya existen. Arrancar directamente con Milestone B (frontend completo).

## Milestones pendientes

- Milestone B (next) — frontend completo (catálogo público + admin UI + carrito + checkout + historial de pedidos + admin orders UI)
- Milestone C — deploy prod (Hetzner + dominio + Resend + credenciales MP reales)

Milestone C está bloqueado sin dominio + credenciales externas.

## Decisiones fuera de scope
- Stripe + PayPal providers: el código tiene la abstracción `PaymentProvider` lista, pero NO se implementan en MVP. Solo MercadoPago.
- Resend integration real: los emails son stubs a structlog. Integrar cuando haya API key.
- Carrier shipping quoting: shipping_cents es fijo (pickup=0, standard=500 ARS) hasta integración con correo.
