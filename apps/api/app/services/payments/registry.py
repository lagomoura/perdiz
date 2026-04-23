"""Provider registry — one place to swap implementations for tests."""

from __future__ import annotations

from app.services.payments.base import PaymentProvider
from app.services.payments.mercadopago import MercadoPagoProvider

_overrides: dict[str, PaymentProvider] = {}


def get_provider(name: str) -> PaymentProvider:
    if name in _overrides:
        return _overrides[name]
    if name == "mercadopago":
        return MercadoPagoProvider()
    raise ValueError(f"unknown payment provider: {name}")


def set_provider_override(name: str, provider: PaymentProvider | None) -> None:
    """Testing hook — replace the registered provider for ``name``."""
    if provider is None:
        _overrides.pop(name, None)
    else:
        _overrides[name] = provider
