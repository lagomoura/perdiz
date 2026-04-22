"""Login lockout backed by Redis.

After 10 failed attempts on the same email within a 15-minute sliding window,
the account is locked for 30 minutes. A successful login clears the counter.
"""
from __future__ import annotations

from typing import Protocol

import redis.asyncio as aioredis

from app.config import settings

_FAIL_WINDOW_SECONDS = 900
_LOCK_DURATION_SECONDS = 1800
_FAIL_THRESHOLD = 10


class _RedisLike(Protocol):
    async def incr(self, key: str) -> int: ...
    async def expire(self, key: str, seconds: int) -> bool: ...
    async def get(self, key: str) -> str | None: ...
    async def delete(self, *keys: str) -> int: ...
    async def setex(self, key: str, seconds: int, value: str) -> bool: ...


_client: aioredis.Redis | None = None


def get_redis() -> _RedisLike:
    global _client
    if _client is None:
        _client = aioredis.from_url(settings.redis_url, decode_responses=True)
    return _client


def _fail_key(email: str) -> str:
    return f"lockout:fail:{email.lower()}"


def _lock_key(email: str) -> str:
    return f"lockout:lock:{email.lower()}"


async def is_locked(email: str) -> bool:
    r = get_redis()
    return bool(await r.get(_lock_key(email)))


async def record_failure(email: str) -> int:
    r = get_redis()
    key = _fail_key(email)
    count = await r.incr(key)
    if count == 1:
        await r.expire(key, _FAIL_WINDOW_SECONDS)
    if count >= _FAIL_THRESHOLD:
        await r.setex(_lock_key(email), _LOCK_DURATION_SECONDS, "1")
    return count


async def clear(email: str) -> None:
    r = get_redis()
    await r.delete(_fail_key(email), _lock_key(email))
