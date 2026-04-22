"""Transactional email stubs.

In dev (no RESEND_API_KEY), the verification link is logged to stdout so the
developer can copy-paste it into the browser. Resend integration lands in a
follow-up PR.
"""
from __future__ import annotations

import structlog

from app.config import settings

log = structlog.get_logger(__name__)


async def send_verification_email(*, to: str, token_plain: str) -> None:
    link = f"{settings.web_base_url}/auth/verificar-email?token={token_plain}"
    if not settings.resend_api_key:
        log.info(
            "email.dev_stub",
            kind="verify_email",
            to=_mask_email(to),
            link=link,
        )
        return
    # TODO(email): integrate Resend SDK + MJML templates in follow-up PR.
    log.info("email.send_queued", kind="verify_email", to=_mask_email(to))


def _mask_email(email: str) -> str:
    local, _, domain = email.partition("@")
    if not domain:
        return "***"
    visible = local[0] if local else "*"
    return f"{visible}***@{domain}"
