# Claude Code — plugins y skills habilitados

En la próxima máquina instalá estos plugins con `/plugin install <name>` (o desde el marketplace de Claude Code) para reproducir el setup.

## Plugins habilitados (de `~/.claude/settings.json`)

```jsonc
"enabledPlugins": {
  "telegram@claude-plugins-official": true,
  "autoresearch@autoresearch": true,
  "frontend-design@claude-plugins-official": true
}
```

### Marketplace extra registrado

```jsonc
"extraKnownMarketplaces": {
  "autoresearch": {
    "source": {
      "source": "github",
      "repo": "uditgoenka/autoresearch"
    }
  }
}
```

Para registrarlo: `/plugin marketplace add github:uditgoenka/autoresearch`.

## Skills usadas en este proyecto

Skills built-in / vía plugins que se invocaron en sesiones recientes:

- `update-config` — para tocar `settings.json` (hooks, permissions, env vars)
- `keybindings-help` — keybindings personales
- `simplify` — code review post-edit
- `fewer-permission-prompts` — generar allowlist en `.claude/settings.json` desde transcripts
- `loop` — tareas recurrentes
- `schedule` — agentes background programados
- `claude-api` — apps con Anthropic SDK
- `frontend-design:frontend-design` — UI distinta de la genérica AI
- `autoresearch:autoresearch` — loops autónomos modificar/verificar
- `autoresearch:autoresearch:debug`, `:fix`, `:plan`, `:ship`, `:security`, `:scenario`, `:predict`, `:learn`
- `telegram:configure`, `telegram:access` — setup del canal de Telegram (para notificaciones, requiere bot token)
- `init` — para generar/actualizar este `CLAUDE.md`
- `review` — review de PRs
- `security-review` — security review del branch actual

## Settings de usuario

`~/.claude/settings.json` actual (de esta máquina):

```jsonc
{
  "permissions": {
    "defaultMode": "auto"
  },
  "model": "opus",
  "enabledPlugins": {
    "telegram@claude-plugins-official": true,
    "autoresearch@autoresearch": true,
    "frontend-design@claude-plugins-official": true
  },
  "extraKnownMarketplaces": {
    "autoresearch": {
      "source": {
        "source": "github",
        "repo": "uditgoenka/autoresearch"
      }
    }
  },
  "effortLevel": "high",
  "autoDreamEnabled": true,
  "skipDangerousModePermissionPrompt": true,
  "skipAutoPermissionPrompt": true
}
```

## Settings del proyecto

`apps/web/perdiz/.claude/settings.local.json` está gitignored (regla global en `~/.config/git/ignore`), así que no se versiona. Permission allowlist actual:

```jsonc
{
  "permissions": {
    "allow": [
      "Bash(uv run *)",
      "Bash(ssh *)"
    ]
  }
}
```

(Las entradas de imagemagick específicas y de paths absolutos del rebrand no es necesario migrarlas; son one-shot.)

## Cómo restaurar en máquina nueva

```bash
# 1. Cloná el repo
git clone https://github.com/lagomoura/perdiz ~/repos_personal/perdiz
cd ~/repos_personal/perdiz

# 2. Linkeá memory + plans para que Claude Code los levante
mkdir -p ~/.claude/projects/-home-<usuario>-repos-personal-perdiz/
ln -s "$(pwd)/.claude/memory" ~/.claude/projects/-home-<usuario>-repos-personal-perdiz/memory

# 3. Copiá settings de usuario a ~/.claude/settings.json (ver bloque arriba)

# 4. Instalá plugins desde dentro de Claude Code:
#    /plugin marketplace add github:uditgoenka/autoresearch
#    /plugin install autoresearch
#    /plugin install telegram
#    /plugin install frontend-design

# 5. Configurá `apps/api/.env.local` (no versionado): ver apps/api/.env.example
# 6. Levantá la dev compose: ver CLAUDE.md
```
