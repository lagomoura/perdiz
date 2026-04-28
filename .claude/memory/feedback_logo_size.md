---
name: Logo size preference
description: User wants the logo in the header to be 150% larger than the default scaffold size
type: feedback
originSessionId: e4a21e96-1b5e-470a-af8a-cc20daf612e6
---
En el header, el logo debe ser al menos 150% del tamaño original. El scaffold usaba h-10 (40px); usar h-16 (64px) o similar. El logo es ilegible cuando es demasiado pequeño.

**Why:** El usuario lo marcó explícitamente al revisar el header de la primera versión.
**How to apply:** En cualquier componente Header que muestre el logo, usar h-14 o h-16 como mínimo. Nunca h-10 o menos.
