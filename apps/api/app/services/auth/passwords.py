"""Password hashing + verification with argon2id."""

from __future__ import annotations

import re

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerifyMismatchError

from app.exceptions import ValidationError

_hasher = PasswordHasher(time_cost=3, memory_cost=65536, parallelism=1)

_HAS_LETTER = re.compile(r"[A-Za-z]")
_HAS_DIGIT = re.compile(r"[0-9]")


def validate_password(plain: str) -> None:
    if not 10 <= len(plain) <= 128:
        raise ValidationError(
            "La contraseña debe tener entre 10 y 128 caracteres.",
            details={"field": "password"},
        )
    if not _HAS_LETTER.search(plain) or not _HAS_DIGIT.search(plain):
        raise ValidationError(
            "La contraseña debe contener al menos una letra y un número.",
            details={"field": "password"},
        )


def hash_password(plain: str) -> str:
    return _hasher.hash(plain)


def verify_password(plain: str, hashed: str | None) -> bool:
    if not hashed:
        return False
    try:
        return _hasher.verify(hashed, plain)
    except (VerifyMismatchError, InvalidHashError):
        return False


def needs_rehash(hashed: str) -> bool:
    try:
        return _hasher.check_needs_rehash(hashed)
    except InvalidHashError:
        return True
