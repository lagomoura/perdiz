"""Payment provider contract.

Each provider turns an Order into a hosted-checkout URL and can parse /
verify asynchronous webhook notifications. Keeping this narrow lets us
plug Stripe + PayPal in later PRs without touching checkout orchestration.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol


class WebhookSignatureError(Exception):
    """Raised when a webhook payload fails signature verification."""


@dataclass(frozen=True)
class PaymentInitResult:
    provider_payment_id: str
    redirect_url: str
    raw_response: dict[str, Any]


@dataclass(frozen=True)
class WebhookEvent:
    event_id: str
    # Normalised status in {"approved", "rejected", "pending", "refunded"}.
    status: str
    provider_payment_id: str
    # Full raw payload persisted on the Payment for audit/debugging.
    raw: dict[str, Any]


class PaymentProvider(Protocol):
    name: str

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
    ) -> PaymentInitResult: ...

    async def parse_webhook(
        self,
        *,
        headers: dict[str, str],
        raw_body: bytes,
    ) -> WebhookEvent:
        """Validate signature and return a normalised event. Raise
        ``WebhookSignatureError`` if verification fails."""
        ...
