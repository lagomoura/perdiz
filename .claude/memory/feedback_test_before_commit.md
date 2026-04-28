---
name: Always test manually before committing
description: User requires end-to-end or visible manual verification before any git commit, even when automated tests pass
type: feedback
originSessionId: e4a21e96-1b5e-470a-af8a-cc20daf612e6
---
Antes de commitear cualquier cambio, validar **manualmente** el flujo afectado aunque los tests automáticos (pytest, vitest, lint, typecheck, build) ya estén en verde. Esto aplica también a fixes pequeños, no solo a features grandes.

**Why:** El usuario lo estableció tras una secuencia donde yo propuse commitear directamente tras ver los checks pasar. Prefiere un ciclo `cambiar → correr tests automatizados → verificar manualmente → commitear` para evitar pushear regresiones que los tests no cubrieron. También da margen para que el usuario revise desde el IDE antes de congelar el cambio en historia git.

**How to apply:** Después de que los linters/tests pasen, exponer al usuario qué verificar manualmente (endpoint por curl, página en el browser, comando específico) y esperar su confirmación explícita antes de hacer `git commit`. Nunca sugerir "ya paso todo, commiteo" directamente.
