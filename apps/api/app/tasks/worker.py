"""arq worker settings. Populate functions as background jobs are implemented."""

from __future__ import annotations

from typing import Any, ClassVar

from arq.connections import RedisSettings

from app.config import settings


class WorkerSettings:
    functions: ClassVar[list[Any]] = []
    redis_settings = RedisSettings.from_dsn(settings.redis_url)
    job_timeout = 300
