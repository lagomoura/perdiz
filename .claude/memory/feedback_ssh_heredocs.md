---
name: Evitar heredocs al pegar en SSH anidado
description: Cuando el usuario copia bloques bash en sesiones SSH a un VPS, los heredocs se rompen; usar scp/ssh-pipe en vez
type: feedback
originSessionId: a58f8d6a-6cf1-40bc-bc23-568cc9044a91
---
No dar bloques con `cat > file <<'EOF' ... EOF` o `git apply <<'PATCH' ... PATCH` para pegar en una sesión SSH del VPS. El terminal del usuario agrega espacios de indentación al pegar (bracketed paste + readline), y el marcador final (`EOF`, `PATCH`) queda con leading whitespace, entonces bash no lo reconoce como cierre. El heredoc queda abierto → Ctrl+C → el archivo destino queda vacío (lo truncó el `>`). Pasó varias veces en el setup del VPS de producción.

**Why:** Vimos 3 intentos fallidos con heredocs (authorized_keys, patch al compose, .env.production) donde el resultado era archivo de 0 bytes o patch inaplicable por indentación.

**How to apply:** Para transferir archivos o aplicar patches al VPS, usar desde la máquina local:
- `scp /local/file deploy@host:/dest/` (directo)
- `cat local_file | ssh deploy@host "tee /dest/file > /dev/null"` (con chown/chmod después)
- `ssh deploy@host "cat > /dest/file" < local_file`

Para modificar archivos in-place en el server, `sudo sed -i` funciona bien con un solo renglón. Evitar heredocs multilínea completamente en cualquier sesión SSH interactiva del usuario.
