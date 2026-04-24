from __future__ import annotations

from dataclasses import dataclass
from typing import Any, ClassVar

import pytest
from app.config import settings
from app.services.emails import client as email_client
from app.services.emails import orders as order_emails


@dataclass
class _FakeOrder:
    id: str
    total_cents: int
    currency: str
    shipping_method: str


class _Capture:
    calls: ClassVar[list[dict[str, Any]]] = []

    @classmethod
    def reset(cls) -> None:
        cls.calls = []

    @classmethod
    def send(cls, params: dict[str, Any]) -> dict[str, Any]:
        cls.calls.append(params)
        return {"id": "mocked"}


@pytest.fixture(autouse=True)
def _setup(monkeypatch: pytest.MonkeyPatch) -> None:
    _Capture.reset()
    monkeypatch.setattr(settings, "resend_api_key", "re_test_key")
    monkeypatch.setattr(settings, "email_from", "p3rDiz <x@test.dev>")
    monkeypatch.setattr(email_client.resend.Emails, "send", _Capture.send)


async def test_order_confirmed_includes_total_and_short_id() -> None:
    order = _FakeOrder(
        id="01KPYFSTJ2FKARG2F6X5W30XM4",
        total_cents=1_234_500,
        currency="ARS",
        shipping_method="standard",
    )
    await order_emails.send_order_confirmed(to="u@example.com", order=order)  # type: ignore[arg-type]

    assert len(_Capture.calls) == 1
    call = _Capture.calls[0]
    assert "#30XM4" not in call["subject"]  # last 6, not 5
    assert "30XM4" in call["subject"][-7:]  # "#X30XM4"
    assert "ARS 12.345,00" in call["html"]
    assert "ARS 12.345,00" in call["text"]


async def test_order_shipped_renders_shipping_method() -> None:
    order = _FakeOrder(
        id="0" * 20 + "ABCDEF", total_cents=0, currency="ARS", shipping_method="pickup"
    )
    await order_emails.send_order_shipped(to="u@example.com", order=order)  # type: ignore[arg-type]
    assert "retiro en sucursal" in _Capture.calls[0]["html"]

    _Capture.reset()
    order2 = _FakeOrder(
        id="0" * 20 + "ABCDEF", total_cents=0, currency="ARS", shipping_method="standard"
    )
    await order_emails.send_order_shipped(to="u@example.com", order=order2)  # type: ignore[arg-type]
    assert "envío a domicilio" in _Capture.calls[0]["html"]


async def test_order_refunded_includes_amount() -> None:
    order = _FakeOrder(
        id="0" * 20 + "ABCDEF", total_cents=500_000, currency="ARS", shipping_method="pickup"
    )
    await order_emails.send_order_refunded(to="u@example.com", order=order)  # type: ignore[arg-type]
    assert "ARS 5.000,00" in _Capture.calls[0]["html"]


async def test_order_cancelled_mentions_refund_hint() -> None:
    order = _FakeOrder(
        id="0" * 20 + "ABCDEF", total_cents=1_000, currency="ARS", shipping_method="pickup"
    )
    await order_emails.send_order_cancelled(to="u@example.com", order=order)  # type: ignore[arg-type]
    assert "reembolso" in _Capture.calls[0]["html"].lower()
