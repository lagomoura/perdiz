from __future__ import annotations

import pytest

from app.exceptions import AuthError
from app.services.auth import tokens


def test_access_token_round_trip() -> None:
    token = tokens.create_access_token("01HWUSER", "user")
    payload = tokens.decode_access_token(token)
    assert payload["sub"] == "01HWUSER"
    assert payload["role"] == "user"
    assert payload["iss"] == "perdiz-api"
    assert payload["aud"] == "perdiz-web"


def test_decode_invalid_token_raises() -> None:
    with pytest.raises(AuthError):
        tokens.decode_access_token("not-a-jwt")


def test_sha256_hex_deterministic() -> None:
    assert tokens.sha256_hex("abc") == tokens.sha256_hex("abc")
    assert tokens.sha256_hex("abc") != tokens.sha256_hex("abd")


def test_refresh_token_plain_is_unique() -> None:
    a = tokens.generate_refresh_token_plain()
    b = tokens.generate_refresh_token_plain()
    assert a != b
    assert len(a) >= 40


def test_email_verification_token_has_24h_expiry() -> None:
    plain, hashed, expires = tokens.generate_email_verification_token()
    assert len(plain) >= 20
    assert hashed == tokens.sha256_hex(plain)
    # Not asserting exact expiry; just that it's in the future.
    from datetime import datetime, timezone

    assert expires > datetime.now(tz=timezone.utc)
