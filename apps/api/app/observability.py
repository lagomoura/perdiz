"""Sentry init. No-op if SENTRY_DSN is empty."""
from __future__ import annotations

import sentry_sdk
from sentry_sdk.integrations.asyncio import AsyncioIntegration
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration

from app.config import settings

_SCRUB_KEYS = {"password", "token", "secret", "authorization", "cookie", "refresh_token"}


def _before_send(event: dict, _hint: dict) -> dict | None:  # type: ignore[type-arg]
    # Lightweight scrub: mask headers, extras and request data body values.
    request = event.get("request") or {}
    for bucket_key in ("headers", "cookies", "data"):
        bucket = request.get(bucket_key)
        if isinstance(bucket, dict):
            for k in list(bucket):
                if k.lower() in _SCRUB_KEYS:
                    bucket[k] = "***"
    return event


def init_observability() -> None:
    if not settings.sentry_dsn:
        return
    sentry_sdk.init(
        dsn=settings.sentry_dsn,
        environment=settings.app_env,
        traces_sample_rate=settings.sentry_traces_sample_rate,
        send_default_pii=False,
        integrations=[
            FastApiIntegration(),
            SqlalchemyIntegration(),
            AsyncioIntegration(),
        ],
        before_send=_before_send,
    )
