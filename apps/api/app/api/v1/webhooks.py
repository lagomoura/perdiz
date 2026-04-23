"""Public webhook endpoints for payment providers.

These MUST be accessible without auth (providers only know their own
credentials). Authentication is the HMAC signature validated inside the
provider's ``parse_webhook``.
"""

from __future__ import annotations

import structlog
from fastapi import APIRouter, Header, HTTPException, Request, status

from app.api.deps import DbSession
from app.exceptions import NotFoundError
from app.services.checkout import webhook as webhook_service
from app.services.payments import get_provider
from app.services.payments.base import WebhookSignatureError

router = APIRouter(prefix="/webhooks", tags=["webhooks"])
log = structlog.get_logger()


@router.post("/mercadopago", status_code=200)
async def mercadopago_webhook(
    request: Request,
    db: DbSession,
    x_signature: str | None = Header(default=None, alias="x-signature"),
    x_request_id: str | None = Header(default=None, alias="x-request-id"),
) -> dict[str, str]:
    raw_body = await request.body()
    # Pass ALL headers — the provider decides which ones to validate.
    headers = {k.lower(): v for k, v in request.headers.items()}
    provider = get_provider("mercadopago")
    try:
        event = await provider.parse_webhook(headers=headers, raw_body=raw_body)
    except WebhookSignatureError as exc:
        log.warning(
            "mercadopago.webhook.invalid_signature",
            reason=str(exc),
            x_request_id=x_request_id,
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid signature"
        ) from exc

    try:
        await webhook_service.process_event(db, provider_name="mercadopago", event=event)
    except NotFoundError:
        # Returning 200 on unknown orders avoids a retry storm from MP for
        # events that belong to another environment sharing credentials.
        log.warning(
            "mercadopago.webhook.order_not_found",
            event_id=event.event_id,
            reference=event.provider_payment_id,
        )
        return {"status": "ignored"}

    return {"status": "ok"}
