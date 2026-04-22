"""Pydantic v2 schemas for auth endpoints."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)


class RegisterIn(_Strict):
    email: EmailStr
    password: str = Field(min_length=10, max_length=128)
    first_name: str | None = Field(default=None, max_length=80)
    last_name: str | None = Field(default=None, max_length=80)


class UserPublic(_Strict):
    id: str
    email: EmailStr
    email_verified: bool
    role: str
    first_name: str | None
    last_name: str | None

    @classmethod
    def from_model(cls, user) -> UserPublic:  # type: ignore[no-untyped-def]
        return cls(
            id=user.id,
            email=user.email,
            email_verified=user.email_verified_at is not None,
            role=user.role,
            first_name=user.first_name,
            last_name=user.last_name,
        )


class RegisterOut(_Strict):
    user: UserPublic


class LoginIn(_Strict):
    email: EmailStr
    password: str


class LoginOut(_Strict):
    access_token: str
    user: UserPublic


class RefreshOut(_Strict):
    access_token: str


class VerifyEmailIn(_Strict):
    token: str


class MessageOut(_Strict):
    message: str


class ForgotPasswordIn(_Strict):
    email: EmailStr


class MeOut(_Strict):
    user: UserPublic


class EmailVerificationOut(_Strict):
    user: UserPublic
    verified_at: datetime
