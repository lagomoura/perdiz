"""Order lifecycle emails — confirmation, shipped, cancelled, refunded.

These are called from webhooks and admin transitions. They must never
raise: dev logs via structlog; prod path with Resend is a TODO (lands
with the email-provider integration PR).
"""

from __future__ import annotations

import structlog

from app.config import settings
from app.models.order import Order

log = structlog.get_logger(__name__)


async def send_order_confirmed(*, to: str, order: Order) -> None:
    await _send(
        kind="order_confirmed",
        to=to,
        subject=f"Confirmamos tu pedido #{_short(order.id)}",
        context={
            "order_id": order.id,
            "total_cents": order.total_cents,
            "currency": order.currency,
        },
    )


async def send_order_shipped(*, to: str, order: Order) -> None:
    await _send(
        kind="order_shipped",
        to=to,
        subject=f"Tu pedido #{_short(order.id)} está en camino",
        context={"order_id": order.id, "shipping_method": order.shipping_method},
    )


async def send_order_cancelled(*, to: str, order: Order) -> None:
    await _send(
        kind="order_cancelled",
        to=to,
        subject=f"Tu pedido #{_short(order.id)} fue cancelado",
        context={"order_id": order.id},
    )


async def send_order_refunded(*, to: str, order: Order) -> None:
    await _send(
        kind="order_refunded",
        to=to,
        subject=f"Reembolso del pedido #{_short(order.id)}",
        context={"order_id": order.id, "total_cents": order.total_cents},
    )


async def _send(
    *,
    kind: str,
    to: str,
    subject: str,
    context: dict[str, object],
) -> None:
    try:
        if not settings.resend_api_key:
            log.info(
                "email.dev_stub",
                kind=kind,
                to=_mask_email(to),
                subject=subject,
                context=context,
            )
            return
        # TODO(email): integrate Resend SDK + MJML templates.
        log.info("email.send_queued", kind=kind, to=_mask_email(to))
    except Exception as exc:  # pragma: no cover - logging-only guard
        log.warning("email.send_failed", kind=kind, error=str(exc))


def _mask_email(email: str) -> str:
    local, _, domain = email.partition("@")
    if not domain:
        return "***"
    visible = local[0] if local else "*"
    return f"{visible}***@{domain}"


def _short(order_id: str) -> str:
    return order_id[-6:]
