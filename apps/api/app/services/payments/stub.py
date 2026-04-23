"""In-memory payment provider used by tests. Deterministic, no network."""

from __future__ import annotations

import hashlib
import hmac
import json
from typing import Any

from app.services.payments.base import (
    PaymentInitResult,
    WebhookEvent,
    WebhookSignatureError,
)

STUB_SECRET = "stub-webhook-secret"


class StubPaymentProvider:
    name = "mercadopago"

    async def create_checkout(
        self,
        *,
        order_id: str,
        amount_cents: int,
        currency: str,
        description: str,
        success_url: str,
        failure_url: str,
        pending_url: str,
        notification_url: str,
        external_reference: str,
    ) -> PaymentInitResult:
        provider_payment_id = f"stub-pref-{order_id}"
        return PaymentInitResult(
            provider_payment_id=provider_payment_id,
            redirect_url=f"https://stub.local/checkout/{provider_payment_id}",
            raw_response={
                "id": provider_payment_id,
                "init_point": f"https://stub.local/checkout/{provider_payment_id}",
                "external_reference": external_reference,
                "amount": amount_cents,
                "currency": currency,
            },
        )

    async def parse_webhook(
        self,
        *,
        headers: dict[str, str],
        raw_body: bytes,
    ) -> WebhookEvent:
        signature = headers.get("x-signature") or headers.get("X-Signature")
        if not signature:
            raise WebhookSignatureError("missing signature")
        expected = hmac.new(STUB_SECRET.encode(), raw_body, hashlib.sha256).hexdigest()
        if not hmac.compare_digest(signature, expected):
            raise WebhookSignatureError("invalid signature")
        try:
            payload: dict[str, Any] = json.loads(raw_body.decode())
        except json.JSONDecodeError as exc:
            raise WebhookSignatureError("invalid json") from exc
        return WebhookEvent(
            event_id=str(payload["id"]),
            status=payload["status"],
            provider_payment_id=payload["provider_payment_id"],
            raw=payload,
        )


def sign_stub_payload(body: bytes) -> str:
    """Test helper — sign a payload with the stub secret."""
    return hmac.new(STUB_SECRET.encode(), body, hashlib.sha256).hexdigest()
