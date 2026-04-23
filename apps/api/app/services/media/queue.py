"""Thin arq enqueue helper. Lives in the service layer so both the admin
upload flow and the tests can call it / swap it out without touching
``app/tasks``.
"""

from __future__ import annotations

import structlog
from arq import create_pool
from arq.connections import RedisSettings

from app.config import settings

log = structlog.get_logger(__name__)


async def enqueue_stl_conversion(stl_media_file_id: str) -> None:
    """Enqueue ``convert_stl_to_glb`` for the given STL media file.

    Failures are logged but don't propagate — the admin commit already
    succeeded and a missed conversion can be retried by re-uploading or
    by an ops-level reconciliation job.
    """
    try:
        redis = await create_pool(RedisSettings.from_dsn(settings.redis_url))
    except Exception as exc:
        log.warning("arq.enqueue.pool_failed", error=str(exc))
        return
    try:
        await redis.enqueue_job("convert_stl_to_glb", stl_media_file_id)
        log.info("arq.enqueue.stl_conversion", media_file_id=stl_media_file_id)
    except Exception as exc:
        log.warning(
            "arq.enqueue.job_failed",
            media_file_id=stl_media_file_id,
            error=str(exc),
        )
    finally:
        await redis.aclose()
