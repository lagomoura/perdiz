from __future__ import annotations

from typing import Any

import pytest
from app.config import settings
from app.services.emails import client as email_client


class _Capture:
    params: dict[str, Any] | None = None
    should_raise: Exception | None = None

    @classmethod
    def reset(cls) -> None:
        cls.params = None
        cls.should_raise = None

    @classmethod
    def send(cls, params: dict[str, Any]) -> dict[str, Any]:
        if cls.should_raise is not None:
            raise cls.should_raise
        cls.params = params
        return {"id": "mocked-id-123"}


@pytest.fixture(autouse=True)
def _reset_capture() -> None:
    _Capture.reset()


async def test_send_email_stubs_when_no_api_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "resend_api_key", "")
    monkeypatch.setattr(email_client.resend.Emails, "send", _Capture.send)

    await email_client.send_email(
        to="user@example.com", subject="hi", html="<p>hi</p>", kind="test"
    )

    assert _Capture.params is None  # SDK not called


async def test_send_email_calls_resend_sdk(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "resend_api_key", "re_test_key")
    monkeypatch.setattr(settings, "email_from", "p3rDiz <no-reply@test.dev>")
    monkeypatch.setattr(email_client.resend.Emails, "send", _Capture.send)

    await email_client.send_email(
        to="user@example.com",
        subject="Asunto",
        html="<p>cuerpo</p>",
        text="cuerpo",
        kind="verify_email",
    )

    assert _Capture.params == {
        "from": "p3rDiz <no-reply@test.dev>",
        "to": ["user@example.com"],
        "subject": "Asunto",
        "html": "<p>cuerpo</p>",
        "text": "cuerpo",
    }


async def test_send_email_swallows_sdk_errors(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "resend_api_key", "re_test_key")
    monkeypatch.setattr(email_client.resend.Emails, "send", _Capture.send)
    _Capture.should_raise = RuntimeError("Resend down")

    # Must not propagate — business flows never break because of email delivery.
    await email_client.send_email(to="user@example.com", subject="x", html="<p>x</p>", kind="test")


async def test_send_email_omits_text_when_none(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "resend_api_key", "re_test_key")
    monkeypatch.setattr(email_client.resend.Emails, "send", _Capture.send)

    await email_client.send_email(to="user@example.com", subject="x", html="<p>x</p>", kind="test")

    assert _Capture.params is not None
    assert "text" not in _Capture.params
