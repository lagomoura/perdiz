"""arq worker settings. Add new jobs to ``functions`` as they land.

Run in dev alongside the API:
    uv run arq app.tasks.worker.WorkerSettings
"""

from __future__ import annotations

from typing import Any, ClassVar

from arq.connections import RedisSettings

from app.config import settings
from app.logging import configure_logging
from app.tasks.media import convert_stl_to_glb


async def _on_startup(_ctx: dict[str, Any]) -> None:
    configure_logging()


class WorkerSettings:
    functions: ClassVar[list[Any]] = [convert_stl_to_glb]
    on_startup = _on_startup
    redis_settings = RedisSettings.from_dsn(settings.redis_url)
    job_timeout = 300
    max_jobs = 4
