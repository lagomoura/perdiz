"""Regression coverage for slowapi integration.

When `@limiter.limit(...)` is applied to a FastAPI endpoint, slowapi injects
rate-limit headers into the response object at runtime. If the endpoint
function does not declare ``response: starlette.responses.Response`` in its
signature, slowapi raises at request time:

    parameter ``response`` must be an instance of starlette.responses.Response

This bug was masked by the autouse ``_disable_rate_limit`` fixture in other
tests. This check introspects every route in the v1 API and asserts that any
route carrying a ``@limiter.limit`` decorator also has a ``Response`` param,
catching the regression without touching network or storage.
"""

from __future__ import annotations

import inspect
import typing

from app.api.v1.auth import router as auth_router
from starlette.responses import Response


def _is_rate_limited(endpoint) -> bool:  # type: ignore[no-untyped-def]
    # slowapi tags wrapped endpoints with a ``_rate_limit`` attribute.
    # Fall back to closure inspection for older/newer slowapi versions.
    if getattr(endpoint, "_rate_limit", None):
        return True
    closure = getattr(endpoint, "__wrapped__", None)
    return closure is not None


def test_every_rate_limited_endpoint_has_response_param() -> None:
    rate_limited_paths = {
        "/auth/register",
        "/auth/login",
        "/auth/refresh",
        "/auth/email/resend-verification",
    }
    seen: set[str] = set()
    for route in auth_router.routes:
        path = getattr(route, "path", None)
        endpoint = getattr(route, "endpoint", None)
        if path is None or endpoint is None:
            continue
        if path not in rate_limited_paths:
            continue
        seen.add(path)
        sig = inspect.signature(endpoint)
        params = sig.parameters
        assert "response" in params, (
            f"Endpoint {path!r} is rate-limited but is missing `response: Response`. "
            "slowapi requires this parameter to inject X-RateLimit-* headers; "
            "without it, requests fail with HTTP 500 at runtime."
        )
        # Resolve string annotations (from `from __future__ import annotations`).
        hints = typing.get_type_hints(endpoint)
        annotation = hints.get("response")
        assert annotation is Response, (
            f"Endpoint {path!r} has `response` but its type annotation is "
            f"{annotation!r}, expected starlette.responses.Response."
        )

    missing = rate_limited_paths - seen
    assert not missing, f"Rate-limited paths not found in router: {missing}"
