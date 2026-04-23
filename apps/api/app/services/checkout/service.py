"""Checkout orchestration.

Flow for ``POST /v1/checkout``:

1. Render the user's open cart (re-computes prices server-side).
2. Validate: not empty, coupon (if any) is still valid, min_order_cents met.
3. Snapshot cart → create Order + OrderItems + status history.
4. Mark cart ``converted`` and drop its coupon link so a later "open" cart
   starts clean. The partial unique index on ``(user_id) WHERE status='open'``
   means the next cart-read will create a fresh one.
5. Record coupon redemption (tracked for max_uses accounting).
6. Create Payment row (pending) and ask the provider to mint a checkout URL.
7. Persist provider_payment_id on the Payment.

Anything that throws after step 3 leaves the order in ``pending_payment``;
the webhook eventually reconciles it, or cron will expire it.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.exceptions import BusinessRuleViolation
from app.models.cart import Cart
from app.models.coupon import Coupon
from app.models.order import Order
from app.models.payment import Payment
from app.models.user import User
from app.repositories import orders as orders_repo
from app.services.cart import service as cart_service
from app.services.payments import PaymentProvider, get_provider


@dataclass(frozen=True)
class CheckoutResult:
    order: Order
    payment: Payment
    redirect_url: str


async def start_checkout(
    db: AsyncSession,
    *,
    user: User,
    shipping_address: dict[str, Any],
    shipping_method: str,
    payment_provider_name: str,
) -> CheckoutResult:
    view = await cart_service.render(db, user=user)
    cart = view.cart
    if not view.items:
        raise BusinessRuleViolation("El carrito está vacío.")

    totals = view.totals
    if totals.total_cents <= 0:
        raise BusinessRuleViolation("El total del pedido debe ser mayor a cero.")

    coupon: Coupon | None = view.coupon
    if coupon is not None and totals.subtotal_cents < coupon.min_order_cents:
        raise BusinessRuleViolation("El subtotal no alcanza el mínimo requerido por el cupón.")

    shipping_cents = _shipping_cost_cents(shipping_method)
    discount_cents = totals.automatic_discounts_cents + totals.coupon_discount_cents
    total_cents = totals.subtotal_cents - discount_cents + shipping_cents

    order = await orders_repo.create_order(
        db,
        user_id=user.id,
        status="pending_payment",
        subtotal_cents=totals.subtotal_cents,
        discount_cents=discount_cents,
        shipping_cents=shipping_cents,
        total_cents=total_cents,
        currency="ARS",
        coupon_id=coupon.id if coupon else None,
        shipping_address_json=shipping_address,
        shipping_method=shipping_method,
    )

    for item in view.items:
        product, _img = view.item_context[item.id]
        line_total = (item.unit_price_cents + item.modifiers_total_cents) * item.quantity
        await orders_repo.create_item(
            db,
            order_id=order.id,
            product_id=item.product_id,
            product_name_snapshot=product.name,
            quantity=item.quantity,
            unit_price_cents=item.unit_price_cents,
            modifiers_total_cents=item.modifiers_total_cents,
            line_total_cents=line_total,
            customizations=item.customizations,
        )

    await orders_repo.create_status_history(
        db,
        order_id=order.id,
        from_status=None,
        to_status="pending_payment",
        changed_by=user.id,
        note="checkout.started",
    )

    if coupon is not None:
        await orders_repo.record_coupon_redemption(
            db, coupon_id=coupon.id, order_id=order.id, user_id=user.id
        )

    _convert_cart(cart)

    payment = await orders_repo.create_payment(
        db,
        order_id=order.id,
        provider=payment_provider_name,
        provider_payment_id="",
        status="pending",
        amount_cents=total_cents,
        currency="ARS",
    )

    provider: PaymentProvider = get_provider(payment_provider_name)
    result = await provider.create_checkout(
        order_id=order.id,
        amount_cents=total_cents,
        currency="ARS",
        description=f"p3rDiz · pedido #{order.id[-6:]}",
        success_url=f"{settings.web_base_url}/checkout/success?order={order.id}",
        failure_url=f"{settings.web_base_url}/checkout/failure?order={order.id}",
        pending_url=f"{settings.web_base_url}/checkout/pending?order={order.id}",
        notification_url=f"{settings.app_base_url}/v1/webhooks/{payment_provider_name}",
        external_reference=order.id,
    )
    payment.provider_payment_id = result.provider_payment_id
    await db.commit()
    await db.refresh(order)
    await db.refresh(payment)

    return CheckoutResult(order=order, payment=payment, redirect_url=result.redirect_url)


def _shipping_cost_cents(method: str) -> int:
    # Placeholder — real quoting lives in PR A4 (shipping integration).
    # Keeping the split so checkout always stores a canonical number.
    if method == "pickup":
        return 0
    return 500_00  # ARS 500 flat until carrier integration lands.


def _convert_cart(cart: Cart) -> None:
    cart.status = "converted"
    cart.coupon_id = None
    cart.updated_at = datetime.now(tz=UTC)
