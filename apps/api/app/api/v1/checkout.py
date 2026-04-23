"""Checkout endpoint — turns the user's open cart into an Order + payment."""

from __future__ import annotations

from fastapi import APIRouter

from app.api.deps import CurrentVerifiedUser, DbSession
from app.schemas.checkout import CheckoutIn, CheckoutOut
from app.services.checkout import service as checkout_service

router = APIRouter(prefix="/checkout", tags=["checkout"])


@router.post("", response_model=CheckoutOut, status_code=201)
async def start_checkout(
    payload: CheckoutIn, db: DbSession, user: CurrentVerifiedUser
) -> CheckoutOut:
    result = await checkout_service.start_checkout(
        db,
        user=user,
        shipping_address=payload.shipping_address.model_dump(),
        shipping_method=payload.shipping_method,
        payment_provider_name=payload.payment_provider,
    )
    return CheckoutOut(
        order_id=result.order.id,
        payment_id=result.payment.id,
        provider=payload.payment_provider,
        redirect_url=result.redirect_url,
        total_cents=result.order.total_cents,
    )
