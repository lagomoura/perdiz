"""arq worker settings. Populate functions as background jobs are implemented."""
from __future__ import annotations

from arq.connections import RedisSettings

from app.config import settings


class WorkerSettings:
    functions: list = []  # type: ignore[type-arg]
    redis_settings = RedisSettings.from_dsn(settings.redis_url)
    job_timeout = 300
