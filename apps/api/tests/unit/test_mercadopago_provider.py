"""Unit tests for the real MercadoPago provider: signature + API calls."""

from __future__ import annotations

import hashlib
import hmac
import json

import httpx
import pytest
import respx
from app.services.payments.base import WebhookSignatureError
from app.services.payments.mercadopago import MercadoPagoProvider

ACCESS_TOKEN = "test-token"
WEBHOOK_SECRET = "test-secret"


def _sig(secret: str, template: str) -> str:
    return hmac.new(secret.encode(), template.encode(), hashlib.sha256).hexdigest()


@respx.mock
async def test_create_checkout_posts_preferences_and_returns_init_point() -> None:
    route = respx.post("https://api.mercadopago.com/checkout/preferences").mock(
        return_value=httpx.Response(
            201,
            json={
                "id": "pref-abc",
                "init_point": "https://www.mercadopago.com.ar/checkout/v1/redirect?pref_id=pref-abc",
                "sandbox_init_point": "https://sandbox.mercadopago.com/...",
            },
        )
    )
    provider = MercadoPagoProvider(access_token=ACCESS_TOKEN, webhook_secret=WEBHOOK_SECRET)
    result = await provider.create_checkout(
        order_id="01HORDER",
        amount_cents=12345,
        currency="ARS",
        description="pedido test",
        success_url="https://web/success",
        failure_url="https://web/failure",
        pending_url="https://web/pending",
        notification_url="https://api/webhook",
        external_reference="01HORDER",
    )
    assert result.provider_payment_id == "pref-abc"
    assert "pref-abc" in result.redirect_url

    sent = json.loads(route.calls.last.request.content)
    assert sent["external_reference"] == "01HORDER"
    assert sent["notification_url"] == "https://api/webhook"
    assert sent["items"][0]["unit_price"] == 123.45
    assert sent["back_urls"]["success"] == "https://web/success"
    assert route.calls.last.request.headers["Authorization"] == f"Bearer {ACCESS_TOKEN}"


async def test_parse_webhook_rejects_missing_signature() -> None:
    provider = MercadoPagoProvider(access_token=ACCESS_TOKEN, webhook_secret=WEBHOOK_SECRET)
    with pytest.raises(WebhookSignatureError):
        await provider.parse_webhook(headers={}, raw_body=b"{}")


async def test_parse_webhook_rejects_malformed_signature() -> None:
    provider = MercadoPagoProvider(access_token=ACCESS_TOKEN, webhook_secret=WEBHOOK_SECRET)
    with pytest.raises(WebhookSignatureError):
        await provider.parse_webhook(headers={"x-signature": "no-equals-sign"}, raw_body=b"{}")


async def test_parse_webhook_rejects_wrong_signature() -> None:
    provider = MercadoPagoProvider(access_token=ACCESS_TOKEN, webhook_secret=WEBHOOK_SECRET)
    body = b'{"id":"evt","data":{"id":"pay-1"}}'
    headers = {"x-signature": "ts=123,v1=deadbeef", "x-request-id": "req-1"}
    with pytest.raises(WebhookSignatureError):
        await provider.parse_webhook(headers=headers, raw_body=body)


@respx.mock
async def test_parse_webhook_happy_path() -> None:
    respx.get("https://api.mercadopago.com/v1/payments/pay-1").mock(
        return_value=httpx.Response(
            200,
            json={
                "id": "pay-1",
                "status": "approved",
                "external_reference": "01HORDER",
            },
        )
    )
    provider = MercadoPagoProvider(access_token=ACCESS_TOKEN, webhook_secret=WEBHOOK_SECRET)
    body = json.dumps(
        {"id": "evt-42", "action": "payment.updated", "data": {"id": "pay-1"}}
    ).encode()
    ts = "1700000000"
    req_id = "req-abc"
    template = f"id:pay-1;request-id:{req_id};ts:{ts};"
    sig = _sig(WEBHOOK_SECRET, template)
    headers = {"x-signature": f"ts={ts},v1={sig}", "x-request-id": req_id}

    event = await provider.parse_webhook(headers=headers, raw_body=body)

    assert event.event_id == "evt-42"
    assert event.status == "approved"
    assert event.provider_payment_id == "01HORDER"
    assert event.raw["payment"]["id"] == "pay-1"


@respx.mock
async def test_parse_webhook_normalises_rejected_and_refunded() -> None:
    for mp_status, expected in [
        ("cancelled", "rejected"),
        ("charged_back", "refunded"),
        ("in_process", "pending"),
    ]:
        respx.get("https://api.mercadopago.com/v1/payments/pay-x").mock(
            return_value=httpx.Response(
                200,
                json={
                    "id": "pay-x",
                    "status": mp_status,
                    "external_reference": "01HORDER",
                },
            )
        )
        provider = MercadoPagoProvider(access_token=ACCESS_TOKEN, webhook_secret=WEBHOOK_SECRET)
        body = json.dumps({"id": "evt", "data": {"id": "pay-x"}}).encode()
        ts = "1700000000"
        template = f"id:pay-x;request-id:req;ts:{ts};"
        sig = _sig(WEBHOOK_SECRET, template)
        event = await provider.parse_webhook(
            headers={"x-signature": f"ts={ts},v1={sig}", "x-request-id": "req"},
            raw_body=body,
        )
        assert event.status == expected
