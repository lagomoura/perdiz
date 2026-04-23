"""Integration-test-only fixtures."""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from app.services.payments import registry
from app.services.payments.stub import StubPaymentProvider


@pytest.fixture
def use_stub_provider() -> Iterator[None]:
    """Swap MercadoPago for the deterministic stub inside the test body.

    Used by order / checkout / webhook tests that don't want to talk to the
    real MP sandbox. Opt-in (non-autouse) so the existing auth tests don't
    needlessly install the override.
    """
    registry.set_provider_override("mercadopago", StubPaymentProvider())
    try:
        yield
    finally:
        registry.set_provider_override("mercadopago", None)
