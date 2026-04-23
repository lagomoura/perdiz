"""User-facing cart endpoints. Require a verified user."""

from __future__ import annotations

from fastapi import APIRouter, Response

from app.api.deps import CurrentVerifiedUser, DbSession
from app.schemas.cart import (
    ApplyCouponIn,
    CartEnvelope,
    CartItemAddIn,
    CartItemOut,
    CartItemUpdateIn,
    CartOut,
    CouponApplied,
)
from app.services.cart import service as cart_service

router = APIRouter(prefix="/cart", tags=["cart"])


def _render_cart_response(view) -> CartOut:  # type: ignore[no-untyped-def]
    items_dto: list[CartItemOut] = []
    for item in view.items:
        ctx = view.item_context.get(item.id)
        if ctx is None:
            continue
        product, image_url = ctx
        line_total = (item.unit_price_cents + item.modifiers_total_cents) * item.quantity
        items_dto.append(
            CartItemOut(
                id=item.id,
                product_id=item.product_id,
                name_snapshot=product.name,
                image_url=image_url,
                quantity=item.quantity,
                unit_price_cents=item.unit_price_cents,
                modifiers_total_cents=item.modifiers_total_cents,
                line_total_cents=line_total,
                customizations=item.customizations,
                warnings=[],
            )
        )
    coupon_out = None
    if view.coupon is not None:
        coupon_out = CouponApplied(
            code=view.coupon.code, type=view.coupon.type, value=view.coupon.value
        )
    return CartOut(
        id=view.cart.id,
        items=items_dto,
        subtotal_cents=view.totals.subtotal_cents,
        automatic_discounts_cents=view.totals.automatic_discounts_cents,
        coupon=coupon_out,
        coupon_discount_cents=view.totals.coupon_discount_cents,
        shipping_cents=view.totals.shipping_cents,
        total_cents=view.totals.total_cents,
    )


@router.get("", response_model=CartEnvelope)
async def get_cart(db: DbSession, user: CurrentVerifiedUser) -> CartEnvelope:
    view = await cart_service.render(db, user=user)
    return CartEnvelope(cart=_render_cart_response(view))


@router.post("/items", response_model=CartEnvelope, status_code=201)
async def add_item(
    payload: CartItemAddIn,
    db: DbSession,
    user: CurrentVerifiedUser,
) -> CartEnvelope:
    await cart_service.add_item(
        db,
        user=user,
        product_id=payload.product_id,
        quantity=payload.quantity,
        raw_selections=[s.model_dump(exclude_none=True) for s in payload.selections],
    )
    view = await cart_service.render(db, user=user)
    return CartEnvelope(cart=_render_cart_response(view))


@router.patch("/items/{item_id}", response_model=CartEnvelope)
async def update_item(
    item_id: str,
    payload: CartItemUpdateIn,
    db: DbSession,
    user: CurrentVerifiedUser,
) -> CartEnvelope:
    raw_selections = (
        [s.model_dump(exclude_none=True) for s in payload.selections]
        if payload.selections is not None
        else None
    )
    await cart_service.update_item(
        db,
        user=user,
        item_id=item_id,
        quantity=payload.quantity,
        raw_selections=raw_selections,
    )
    view = await cart_service.render(db, user=user)
    return CartEnvelope(cart=_render_cart_response(view))


@router.delete("/items/{item_id}", status_code=204)
async def remove_item(item_id: str, db: DbSession, user: CurrentVerifiedUser) -> Response:
    await cart_service.remove_item(db, user=user, item_id=item_id)
    return Response(status_code=204)


@router.post("/coupon", response_model=CartEnvelope)
async def apply_coupon(
    payload: ApplyCouponIn,
    db: DbSession,
    user: CurrentVerifiedUser,
) -> CartEnvelope:
    await cart_service.apply_coupon(db, user=user, code=payload.code)
    view = await cart_service.render(db, user=user)
    return CartEnvelope(cart=_render_cart_response(view))


@router.delete("/coupon", response_model=CartEnvelope)
async def remove_coupon(db: DbSession, user: CurrentVerifiedUser) -> CartEnvelope:
    await cart_service.remove_coupon(db, user=user)
    view = await cart_service.render(db, user=user)
    return CartEnvelope(cart=_render_cart_response(view))
