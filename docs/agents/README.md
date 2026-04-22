# Guía para agentes constructores

Este documento es el **punto de entrada obligatorio** para cualquier agente (humano o automatizado) que vaya a escribir código en este repositorio. Leer **antes** de cualquier edición.

## Regla número 1

**No inventes**. Si un caso no está cubierto por la documentación en `docs/`, **detente** y pídeselo al usuario antes de avanzar. Es preferible preguntar que escribir código que haya que reescribir.

## Regla número 2

**La documentación es vinculante**. Los archivos en `docs/` definen contratos: nombres de tablas, endpoints, tokens de diseño, convenciones. No se desvía sin actualizar el doc en el mismo PR.

## Regla número 3

**Ningún agente toca `main` directamente**. Todo cambio pasa por branch + PR. Convencionalmente el nombre del branch lleva prefijo por tipo (`feat/`, `fix/`, `chore/`, `docs/`).

## Qué leer según la tarea

### Tarea: implementar un endpoint backend
1. `docs/architecture/overview.md` — estructura general
2. `docs/architecture/data-model.md` — entidades relevantes
3. `docs/architecture/security.md` — auth y validaciones
4. `docs/backend/conventions.md` — capas, errores, tests
5. `docs/backend/api-contract.md` — forma del endpoint
6. Sección específica de `docs/product/product-spec.md` que describe la regla de negocio

### Tarea: agregar una pantalla frontend
1. `docs/brand/visual-system.md` — tokens que vas a usar
2. `docs/product/product-spec.md` — qué debe hacer la pantalla
3. `docs/frontend/conventions.md` — estructura, estado, routing
4. `docs/frontend/ui-components.md` — componentes existentes antes de crear uno nuevo
5. `docs/backend/api-contract.md` — endpoints a consumir

### Tarea: agregar / modificar una entidad DB
1. `docs/architecture/data-model.md` — entender el modelo actual y dónde encaja el cambio
2. `docs/backend/conventions.md` — migraciones, repositorios
3. Actualizar **primero el doc** (`data-model.md`) con el nuevo schema; luego generar migración Alembic.

### Tarea: agregar un tipo de personalización nuevo
1. `docs/product/customization-model.md` — flujo completo de extensión
2. Seguir los 5 pasos listados en "Agregar un tipo nuevo en el futuro"

### Tarea: integrar una nueva pasarela de pago o proveedor externo
1. `docs/architecture/overview.md` — stack y ubicación de integraciones
2. `docs/architecture/security.md` — sección webhooks
3. `docs/backend/conventions.md` — patrón de servicios
4. Preguntar al usuario antes de abrir cuenta en servicio pago

### Tarea: cambio de infraestructura o CI/CD
1. `docs/devops/environments.md`
2. `docs/devops/deployment.md`
3. `docs/devops/observability.md`

## Protocolo de trabajo

1. **Entender**: leer los docs aplicables de la tabla de arriba. Si algo no cierra, preguntar al usuario.
2. **Planear**: escribir un plan breve antes de editar. Si el cambio cruza frontend y backend, explicitar el contrato API que los une.
3. **Ejecutar**: un branch por tarea, commits pequeños con Conventional Commits.
4. **Verificar**: correr `lint + typecheck + tests` locales antes de push.
5. **Documentar**: actualizar los docs que correspondan en el mismo PR.
6. **Abrir PR**: descripción con el "por qué"; linkear issue si existe; checklist.

## Cosas que están prohibidas (sin aprobación explícita del usuario)

- Instalar librerías "grandes" que el doc no contempla (si dudas, preguntá).
- Cambiar versiones mayores de dependencias core (React, FastAPI, Postgres).
- Agregar un proveedor externo nuevo que genere costo fijo.
- Modificar `JWT_SECRET`, credenciales o secretos desde la app.
- Borrar datos de producción.
- Ejecutar migraciones destructivas sin plan reversible documentado.
- Hacer `git push --force` a `main` o `staging`.
- Subir secretos a commits o al repo.
- Romper el contrato del API sin versionado (`/v2/...`).
- Agregar features fuera de alcance listado en `product-spec.md` § "Fuera de alcance".

## Qué contrato respetar

- **Endpoints** → tal como se listan en `docs/backend/api-contract.md`. Cambios deben editar ese documento primero.
- **Schemas DB** → tal como se listan en `docs/architecture/data-model.md`. Cambios deben editar ese documento primero.
- **Tokens de diseño** → `docs/brand/visual-system.md`. Cambios deben editar ese documento primero.
- **Códigos de error** → `docs/backend/conventions.md` § "Códigos de error estables". Siempre usar códigos existentes; agregar nuevos al doc antes de usarlos en código.

## Checklist de PR

Todo PR debe incluir en su descripción:

- [ ] Leí los docs aplicables a esta tarea.
- [ ] Actualicé los docs si el cambio introduce algo nuevo.
- [ ] Los tests existentes pasan y agregué tests para lo nuevo si aplica.
- [ ] No introduje secretos en el código ni en logs.
- [ ] Si hay migración: es reversible (o documenté por qué no).
- [ ] Si toca UI: respeta tokens de `visual-system.md` y accesibilidad AA.
- [ ] Si toca el API: el contrato en `api-contract.md` quedó alineado.

## Cómo pedir ayuda

Si un requisito no está claro o entra en conflicto con otro documento, **parar** y plantear al usuario:
- Qué se quiere hacer.
- Qué doc dice qué (referencia línea/sección).
- Cuál es la duda concreta.
- Qué alternativas se ven y cuál recomendás.

Nunca "rellenar" una decisión de producto silenciosamente. Preguntá.
