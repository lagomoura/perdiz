from __future__ import annotations

import pytest
from app.exceptions import ValidationError
from app.services.auth import passwords


def test_hash_and_verify_round_trip() -> None:
    hashed = passwords.hash_password("MyStrongPass1")
    assert passwords.verify_password("MyStrongPass1", hashed)
    assert not passwords.verify_password("WrongPass1234", hashed)


def test_verify_with_none_hash_returns_false() -> None:
    assert passwords.verify_password("whatever", None) is False


def test_validate_password_accepts_ok() -> None:
    passwords.validate_password("GoodPass123")


@pytest.mark.parametrize(
    "pw",
    [
        "short1a",  # < 10
        "a" * 129 + "1",  # > 128
        "onlyletters!",  # no digit
        "1234567890",  # no letter
    ],
)
def test_validate_password_rejects(pw: str) -> None:
    with pytest.raises(ValidationError):
        passwords.validate_password(pw)
