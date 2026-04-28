---
name: Ruff format must cover the whole API package
description: Before committing backend work, run `uv run ruff format --check .` from apps/api/ (not just app/ tests/) so alembic/versions/ and other dirs match what CI verifies
type: feedback
originSessionId: e4a21e96-1b5e-470a-af8a-cc20daf612e6
---
Run `uv run ruff format --check .` from `apps/api/` before committing — not `ruff format app/ tests/`, which is what I did in PR #12.

**Why:** PR #12 CI failed because I only formatted `app/ tests/` locally, so a new `alembic/versions/` file landed un-formatted. CI runs `ruff format --check .` (entire apps/api/ tree), and needed a follow-up PR #13 just to fix the format.

**How to apply:** when touching backend code — especially when the PR creates new files outside `app/` and `tests/` (migrations, scripts, config) — the pre-commit check must be `ruff format --check .` from `apps/api/`. Same for `ruff check .`. The `app/ tests/` shortcut silently misses migrations.
