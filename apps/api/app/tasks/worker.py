"""arq worker settings. Add new jobs to ``functions`` as they land.

Run in dev alongside the API:
    uv run arq app.tasks.worker.WorkerSettings
"""

from __future__ import annotations

from typing import Any, ClassVar

from arq.connections import RedisSettings
from arq.cron import cron

from app.config import settings
from app.logging import configure_logging
from app.tasks.media import cleanup_abandoned_uploads, convert_stl_to_glb


async def _on_startup(_ctx: dict[str, Any]) -> None:
    configure_logging()


class WorkerSettings:
    functions: ClassVar[list[Any]] = [convert_stl_to_glb, cleanup_abandoned_uploads]
    cron_jobs: ClassVar[list[Any]] = [
        # Daily at 02:00 UTC (≈ 23:00 ART off-season). No retries on miss;
        # if the worker was down the next tick picks it up.
        # arq's cron() expects a narrower ``WorkerCoroutine`` alias than what
        # mypy infers from our job's explicit ``-> int`` return; the call
        # works at runtime.
        cron(cleanup_abandoned_uploads, hour=2, minute=0, run_at_startup=False),  # type: ignore[arg-type]
    ]
    on_startup = _on_startup
    redis_settings = RedisSettings.from_dsn(settings.redis_url)
    job_timeout = 300
    max_jobs = 4
