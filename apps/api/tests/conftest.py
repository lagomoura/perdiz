"""Shared pytest fixtures.

Strategy:
- Session-scoped fixture recreates public schema and tables via Base.metadata.
- Per-test autouse cleanup TRUNCATEs everything.
- Per-test autouse patches lockout.Redis with fakeredis and disables slowapi.
"""
from __future__ import annotations

from collections.abc import AsyncIterator

import pytest
import pytest_asyncio
from fakeredis.aioredis import FakeRedis
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text

from app.api.rate_limit import limiter
from app.config import settings
from app.db.base import Base
from app.db.session import AsyncSessionLocal, engine
from app.main import app
from app.services.auth import lockout


@pytest_asyncio.fixture(scope="session", loop_scope="session", autouse=True)
async def _setup_schema() -> AsyncIterator[None]:
    assert settings.app_env != "production", "Refusing to run tests against production"
    async with engine.begin() as conn:
        await conn.execute(text("DROP SCHEMA IF EXISTS public CASCADE"))
        await conn.execute(text("CREATE SCHEMA public"))
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS citext"))
        await conn.run_sync(Base.metadata.create_all)
    yield
    await engine.dispose()


@pytest_asyncio.fixture(autouse=True)
async def _truncate_tables() -> AsyncIterator[None]:
    yield
    if not Base.metadata.sorted_tables:
        return
    async with AsyncSessionLocal() as session:
        tables = ", ".join(f'"{t.name}"' for t in reversed(Base.metadata.sorted_tables))
        await session.execute(text(f"TRUNCATE TABLE {tables} RESTART IDENTITY CASCADE"))
        await session.commit()


@pytest.fixture(autouse=True)
def _patch_lockout_redis(monkeypatch: pytest.MonkeyPatch) -> None:
    fake = FakeRedis(decode_responses=True)
    monkeypatch.setattr(lockout, "_client", fake)


@pytest.fixture(autouse=True)
def _disable_rate_limit() -> None:
    limiter.enabled = False


@pytest_asyncio.fixture
async def client() -> AsyncIterator[AsyncClient]:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
