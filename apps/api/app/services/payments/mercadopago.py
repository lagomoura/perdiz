"""MercadoPago provider.

Uses Preferences API (hosted Checkout Pro) because it's the lowest-friction
path for Argentine consumers and doesn't require PCI scope. Webhook format
follows the ``x-signature`` header introduced in 2023:
``ts=<unix>,v1=<hex>`` where ``v1`` is HMAC-SHA256 over the template
``id:<data.id>;request-id:<x-request-id>;ts:<ts>;``.
"""

from __future__ import annotations

import hashlib
import hmac
import json
from typing import Any

import httpx

from app.config import settings
from app.services.payments.base import (
    PaymentInitResult,
    WebhookEvent,
    WebhookSignatureError,
)

_PREFERENCES_URL = "https://api.mercadopago.com/checkout/preferences"
_PAYMENTS_URL = "https://api.mercadopago.com/v1/payments"

_STATUS_MAP = {
    "approved": "approved",
    "rejected": "rejected",
    "cancelled": "rejected",
    "refunded": "refunded",
    "charged_back": "refunded",
    "in_process": "pending",
    "pending": "pending",
    "authorized": "pending",
}


class MercadoPagoProvider:
    name = "mercadopago"

    def __init__(
        self,
        *,
        access_token: str | None = None,
        webhook_secret: str | None = None,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        self._access_token = access_token or settings.mercadopago_access_token
        self._webhook_secret = webhook_secret or settings.mercadopago_webhook_secret
        self._http = http_client

    async def _client(self) -> httpx.AsyncClient:
        return self._http or httpx.AsyncClient(timeout=10.0)

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
        body = {
            "items": [
                {
                    "title": description,
                    "quantity": 1,
                    "unit_price": round(amount_cents / 100, 2),
                    "currency_id": currency,
                }
            ],
            "external_reference": external_reference,
            "notification_url": notification_url,
            "back_urls": {
                "success": success_url,
                "failure": failure_url,
                "pending": pending_url,
            },
            "auto_return": "approved",
            "metadata": {"order_id": order_id},
        }
        headers = {
            "Authorization": f"Bearer {self._access_token}",
            "Content-Type": "application/json",
        }
        client = await self._client()
        close_client = self._http is None
        try:
            resp = await client.post(_PREFERENCES_URL, json=body, headers=headers)
            resp.raise_for_status()
            data = resp.json()
        finally:
            if close_client:
                await client.aclose()
        return PaymentInitResult(
            provider_payment_id=str(data["id"]),
            redirect_url=data.get("init_point") or data["sandbox_init_point"],
            raw_response=data,
        )

    async def parse_webhook(
        self,
        *,
        headers: dict[str, str],
        raw_body: bytes,
    ) -> WebhookEvent:
        # Normalise header keys — FastAPI already lowercases, but defensive.
        hdr = {k.lower(): v for k, v in headers.items()}
        x_signature = hdr.get("x-signature")
        x_request_id = hdr.get("x-request-id", "")
        if not x_signature:
            raise WebhookSignatureError("missing x-signature header")

        ts, v1 = _split_signature(x_signature)
        try:
            payload: dict[str, Any] = json.loads(raw_body.decode())
        except json.JSONDecodeError as exc:
            raise WebhookSignatureError("invalid json") from exc

        data_id = str(payload.get("data", {}).get("id", ""))
        template = f"id:{data_id};request-id:{x_request_id};ts:{ts};"
        expected = hmac.new(
            self._webhook_secret.encode(), template.encode(), hashlib.sha256
        ).hexdigest()
        if not hmac.compare_digest(expected, v1):
            raise WebhookSignatureError("invalid signature")

        # The webhook only carries the payment id — we must fetch the payment
        # to know its status. Tests stub this out via respx.
        payment = await self._fetch_payment(data_id)
        status = _STATUS_MAP.get(payment.get("status", ""), "pending")
        external_reference = payment.get("external_reference")
        if not external_reference:
            raise WebhookSignatureError("payment missing external_reference")
        return WebhookEvent(
            event_id=str(payload.get("id") or data_id),
            status=status,
            provider_payment_id=str(external_reference),
            raw={"notification": payload, "payment": payment},
        )

    async def _fetch_payment(self, payment_id: str) -> dict[str, Any]:
        headers = {"Authorization": f"Bearer {self._access_token}"}
        client = await self._client()
        close_client = self._http is None
        try:
            resp = await client.get(f"{_PAYMENTS_URL}/{payment_id}", headers=headers)
            resp.raise_for_status()
            return resp.json()  # type: ignore[no-any-return]
        finally:
            if close_client:
                await client.aclose()


def _split_signature(raw: str) -> tuple[str, str]:
    ts = ""
    v1 = ""
    for part in raw.split(","):
        key, _, value = part.strip().partition("=")
        if key == "ts":
            ts = value
        elif key == "v1":
            v1 = value
    if not ts or not v1:
        raise WebhookSignatureError("malformed x-signature header")
    return ts, v1
