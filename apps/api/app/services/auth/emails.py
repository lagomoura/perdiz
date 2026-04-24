"""Auth-related transactional emails (verification)."""

from __future__ import annotations

from app.config import settings
from app.services.emails.client import send_email


async def send_verification_email(*, to: str, token_plain: str) -> None:
    link = f"{settings.web_base_url}/auth/verificar-email?token={token_plain}"
    subject = "Verificá tu email — p3rDiz"
    html = (
        "<p>Hola,</p>"
        "<p>Gracias por registrarte en <strong>p3rDiz</strong>. "
        "Para activar tu cuenta, hacé click en este enlace:</p>"
        f'<p><a href="{link}">{link}</a></p>'
        "<p>El enlace expira en 24 horas.</p>"
        "<p>Si no creaste esta cuenta, ignorá este mensaje.</p>"
    )
    text = (
        "Gracias por registrarte en p3rDiz.\n"
        f"Activá tu cuenta en este enlace: {link}\n"
        "Expira en 24 horas. Si no creaste la cuenta, ignorá este mensaje."
    )
    await send_email(to=to, subject=subject, html=html, text=text, kind="verify_email")
