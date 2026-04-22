# Roles y permisos — p3rDiz

## Roles definidos

Solo dos:

- **`user`** — cualquier persona registrada y verificada. Rol default tras registro.
- **`admin`** — administrador único del sistema. Asignado manualmente en DB (no hay UI para promover usuarios en el MVP).

El modelo de datos contempla un campo `role` enum con extensibilidad futura (p.ej. `operator`, `support`), pero en el MVP solo se usan esos dos valores.

## Matriz de permisos

**Leyenda**: ✓ permitido · ✗ denegado · (o) solo sobre recursos propios · (v) requiere email verificado.

### Catálogo público

| Acción | Anónimo | user (sin verificar) | user (verificado) | admin |
|---|---|---|---|---|
| Ver listado de categorías | ✓ | ✓ | ✓ | ✓ |
| Ver listado de productos | ✓ | ✓ | ✓ | ✓ |
| Ver detalle de producto | ✓ | ✓ | ✓ | ✓ |
| Ver preview 3D | ✓ | ✓ | ✓ | ✓ |
| Buscar / filtrar | ✓ | ✓ | ✓ | ✓ |

### Cuenta

| Acción | Anónimo | user (sin verificar) | user (verificado) | admin |
|---|---|---|---|---|
| Registrarse | ✓ | — | — | — |
| Login (email/pass, Google, Microsoft) | ✓ | ✓ | ✓ | ✓ |
| Verificar email | — | ✓ | — | — |
| Recuperar password | ✓ | ✓ | ✓ | ✓ |
| Ver / editar perfil propio | ✗ | ✓ (o) | ✓ (o) | ✓ (o) |
| Ver / editar direcciones propias | ✗ | ✓ (o) | ✓ (o) | ✓ (o) |

### Carrito y checkout

| Acción | Anónimo | user (sin verificar) | user (verificado) | admin |
|---|---|---|---|---|
| Agregar al carrito | ✗ | ✓ | ✓ | ✓ |
| Modificar carrito propio | ✗ | ✓ (o) | ✓ (o) | ✓ (o) |
| Aplicar cupón | ✗ | ✓ | ✓ | ✓ |
| Confirmar checkout | ✗ | ✗ (v) | ✓ | ✓ |
| Ver historial propio | ✗ | ✓ (o) | ✓ (o) | ✓ (o) |
| Ver detalle de pedido propio | ✗ | ✓ (o) | ✓ (o) | ✓ (o) |
| Cancelar pedido propio (solo si está `pending_payment` o `paid`) | ✗ | ✓ (o) | ✓ (o) | ✓ (o) |

### Wishlist

| Acción | Anónimo | user (verificado) | admin |
|---|---|---|---|
| Ver wishlist propia | ✗ | ✓ (o) | ✓ (o) |
| Agregar / remover | ✗ | ✓ (o) | ✓ (o) |

### Admin

| Acción | user | admin |
|---|---|---|
| Entrar a `/admin` | ✗ (404) | ✓ |
| Dashboard / KPIs | ✗ | ✓ |
| CRUD productos | ✗ | ✓ |
| Subir / reemplazar modelos 3D | ✗ | ✓ |
| CRUD categorías | ✗ | ✓ |
| Ver pedidos de cualquier usuario | ✗ | ✓ |
| Cambiar estado de pedido | ✗ | ✓ |
| Reembolsar pedido | ✗ | ✓ |
| Ver lista de usuarios | ✗ | ✓ |
| Suspender usuario | ✗ | ✓ |
| CRUD cupones y descuentos automáticos | ✗ | ✓ |
| Ver log de auditoría | ✗ | ✓ |
| Editar configuración del sitio | ✗ | ✓ |

## Reglas de acceso

1. **Default deny**: si un endpoint no declara explícitamente qué rol lo puede consumir, se rechaza.
2. **Dependencia de FastAPI obligatoria**: cada endpoint de API usa `Depends(require_role(...))` o `Depends(current_user)` para autorización. Endpoints públicos usan `Depends(optional_user)`.
3. **Ownership check**: cuando un endpoint recibe un `id` de recurso del usuario (pedido, dirección, etc.), la capa de servicio **debe** verificar que el recurso pertenece al `current_user` o que `current_user.role == 'admin'`. La verificación de propiedad vive en la capa de servicio, no en la capa de ruta.
4. **Enumeración**: endpoints administrativos devuelven `404 Not Found` a usuarios sin rol admin, nunca `403 Forbidden`, para no revelar la existencia de la superficie admin.
5. **Auditoría**: toda mutación ejecutada por un admin se registra en `audit_log` automáticamente vía middleware/dependencia. Ver `architecture/security.md`.

## Email verificado — cuándo exigirlo

Bloquean sin verificación:
- Confirmar checkout.
- Cambiar email de la cuenta.

No bloquean:
- Login, navegar catálogo, armar carrito, editar perfil (salvo email), gestionar direcciones, wishlist.

La razón: el usuario debe poder **explorar y armar** antes de comprometerse a verificar. El fricción se cobra en el momento de pagar.
