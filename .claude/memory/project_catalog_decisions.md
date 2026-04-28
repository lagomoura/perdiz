---
name: Catalog decisions
description: Product/category conventions and slug policy decided while building the admin UI
type: project
originSessionId: a58f8d6a-6cf1-40bc-bc23-568cc9044a91
---
**Categorías:** jerarquía **N-niveles** (no uno como dice el docstring de `app/models/category.py`). El admin UI renderiza la lista como árbol aplanado con sangría y excluye la propia + descendientes del selector de padre para prevenir ciclos. Si alguna vez se cambia a una sola profundidad permitida, actualizar `CategoryEditPage` y el helper `descendantIds`.

**Slugs:** autogenerados desde el nombre con `slugify()` (NFD + strip accents + lower + `[^a-z0-9]→-`). El admin puede editarlo a mano; una vez editado (`slugTouched`), dejamos de regenerarlo aunque cambie el nombre. Política idéntica planeada para productos.

**Why:** Decisión explícita del usuario (abril 2026) al empezar a cargar catálogo. La tienda es ideas impresas en 3D, donde las familias se subdividen naturalmente (`Figuritas 3D → Dinosaurios → T-Rex`).

**How to apply:** Al tocar la UI de categorías o el servicio asociado, asumí árbol infinito. Al agregar productos, usá el mismo patrón de slug (autogenerar + permitir override).
