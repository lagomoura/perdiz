# `.claude/` — Estado portable de Claude Code

Snapshot del setup de Claude Code para este proyecto, para restaurar el contexto en una máquina nueva sin perder memoria, planes ni decisiones.

## Layout

- `memory/` — auto-memory del proyecto (perfil del usuario, feedback acumulado, hechos de proyecto, refs externas). Se monta en `~/.claude/projects/<slug>/memory/`.
- `plans/` — planes de plan-mode generados en sesiones pasadas. Útiles para reconstruir por qué se tomaron decisiones grandes (rebrand, redesigns, migraciones).
- `PLUGINS.md` — plugins, skills y settings de usuario para replicar el entorno.
- `settings.local.json` — permissions allowlist del proyecto. **Gitignored** por convención (regla global en `~/.config/git/ignore`).

## Cómo lo usa Claude

- `CLAUDE.md` (en la raíz del repo) se carga automáticamente como contexto en cada sesión. Es el "manual de uso" del proyecto.
- `memory/MEMORY.md` y los archivos linkeados desde ahí se cargan vía el sistema de auto-memory cuando Claude detecta que alguno es relevante para la tarea actual.
- `plans/` no se carga automáticamente — son referencia que Claude (o vos) podés invocar leyéndolas explícitamente.

## Limitaciones

- Las sesiones JSONL (`~/.claude/projects/<slug>/*.jsonl`) **no** se incluyen acá. Son grandes (decenas de MB) y tienen riesgo de leak de secretos pegados en chats anteriores.
- `~/.claude/.credentials.json` **nunca** debe versionarse — son tokens de auth.
- `history.jsonl`, caches, image-cache, paste-cache, shell-snapshots, telemetry — son artefactos efímeros de la máquina, no portables.

## Rebuild en máquina nueva

Ver `PLUGINS.md` § "Cómo restaurar en máquina nueva".
