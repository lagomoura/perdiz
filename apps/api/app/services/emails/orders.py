"""Order lifecycle emails — confirmation, shipped, cancelled, refunded.

Called from webhooks and admin transitions. Must never raise: delivery
failures log but don't break the business operation.
"""

from __future__ import annotations

from app.models.order import Order
from app.services.emails.client import send_email


async def send_order_confirmed(*, to: str, order: Order) -> None:
    total = _format_amount(order.total_cents, order.currency)
    short = _short(order.id)
    subject = f"Confirmamos tu pedido #{short}"
    html = (
        f"<p>¡Gracias por tu compra en <strong>p3rDiz</strong>!</p>"
        f"<p>Confirmamos tu pedido <strong>#{short}</strong>.</p>"
        f"<p>Total: <strong>{total}</strong></p>"
        f"<p>Te avisaremos cuando esté listo para envío.</p>"
    )
    text = (
        f"Gracias por tu compra en p3rDiz.\n"
        f"Pedido #{short} confirmado. Total: {total}.\n"
        f"Te avisaremos cuando esté listo."
    )
    await send_email(to=to, subject=subject, html=html, text=text, kind="order_confirmed")


async def send_order_shipped(*, to: str, order: Order) -> None:
    short = _short(order.id)
    method = "retiro en sucursal" if order.shipping_method == "pickup" else "envío a domicilio"
    subject = f"Tu pedido #{short} está en camino"
    html = f"<p>Tu pedido <strong>#{short}</strong> fue despachado.</p><p>Modalidad: {method}.</p>"
    text = f"Pedido #{short} despachado. Modalidad: {method}."
    await send_email(to=to, subject=subject, html=html, text=text, kind="order_shipped")


async def send_order_cancelled(*, to: str, order: Order) -> None:
    short = _short(order.id)
    subject = f"Tu pedido #{short} fue cancelado"
    html = (
        f"<p>Tu pedido <strong>#{short}</strong> fue cancelado.</p>"
        "<p>Si pagaste, el reembolso se procesa por separado.</p>"
    )
    text = f"Pedido #{short} cancelado. Si pagaste, el reembolso se procesa por separado."
    await send_email(to=to, subject=subject, html=html, text=text, kind="order_cancelled")


async def send_order_refunded(*, to: str, order: Order) -> None:
    total = _format_amount(order.total_cents, order.currency)
    short = _short(order.id)
    subject = f"Reembolso del pedido #{short}"
    html = (
        f"<p>Procesamos el reembolso de tu pedido <strong>#{short}</strong>.</p>"
        f"<p>Monto: <strong>{total}</strong>.</p>"
        "<p>Puede tardar algunos días hábiles en reflejarse según tu medio de pago.</p>"
    )
    text = f"Reembolso del pedido #{short}: {total}. Puede tardar días hábiles en reflejarse."
    await send_email(to=to, subject=subject, html=html, text=text, kind="order_refunded")


def _short(order_id: str) -> str:
    return order_id[-6:]


def _format_amount(cents: int, currency: str) -> str:
    pesos = cents / 100
    # Argentine locale: 1.234,56
    formatted = f"{pesos:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"{currency} {formatted}"
