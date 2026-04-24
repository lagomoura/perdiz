"""Thin wrapper around the Resend SDK.

All transactional emails (auth, orders) go through `send_email`. If
`RESEND_API_KEY` is not configured, the call is logged and dropped: dev and
tests keep working without network. Failures are swallowed and logged —
email delivery must never break a business operation.
"""

from __future__ import annotations

import asyncio
from typing import Any

import resend
import structlog

from app.config import settings

log = structlog.get_logger(__name__)


async def send_email(
    *,
    to: str,
    subject: str,
    html: str,
    text: str | None = None,
    kind: str = "generic",
) -> None:
    if not settings.resend_api_key:
        log.info("email.dev_stub", kind=kind, to=_mask(to), subject=subject)
        return

    resend.api_key = settings.resend_api_key
    params: dict[str, Any] = {
        "from": settings.email_from,
        "to": [to],
        "subject": subject,
        "html": html,
    }
    if text:
        params["text"] = text
    try:
        result = await asyncio.to_thread(resend.Emails.send, params)
        provider_id = result.get("id") if isinstance(result, dict) else None
        log.info("email.sent", kind=kind, to=_mask(to), provider_id=provider_id)
    except Exception as exc:
        # Delivery failures must not break checkout/register flows.
        log.warning("email.send_failed", kind=kind, error=str(exc))


def _mask(email: str) -> str:
    local, _, domain = email.partition("@")
    if not domain:
        return "***"
    visible = local[0] if local else "*"
    return f"{visible}***@{domain}"
