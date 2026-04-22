"""Auth endpoints: register, login, refresh, logout, email verification."""
from __future__ import annotations

from fastapi import APIRouter, Cookie, Request, Response

from app.api.deps import CurrentUser, DbSession
from app.api.rate_limit import limiter
from app.config import settings
from app.schemas.auth import (
    EmailVerificationOut,
    LoginIn,
    LoginOut,
    RefreshOut,
    RegisterIn,
    RegisterOut,
    UserPublic,
    VerifyEmailIn,
)
from app.services.auth import service as auth_service

router = APIRouter(prefix="/auth", tags=["auth"])

REFRESH_COOKIE_NAME = "refresh_token"
REFRESH_COOKIE_PATH = "/v1/auth"


def _set_refresh_cookie(response: Response, plain: str) -> None:
    response.set_cookie(
        key=REFRESH_COOKIE_NAME,
        value=plain,
        httponly=True,
        secure=settings.app_env == "production",
        samesite="lax",
        max_age=settings.jwt_refresh_ttl_seconds,
        path=REFRESH_COOKIE_PATH,
    )


def _clear_refresh_cookie(response: Response) -> None:
    response.delete_cookie(key=REFRESH_COOKIE_NAME, path=REFRESH_COOKIE_PATH)


def _client_meta(request: Request) -> tuple[str | None, str | None]:
    ua = request.headers.get("user-agent")
    ip = request.client.host if request.client else None
    return ua, ip


@router.post("/register", status_code=201, response_model=RegisterOut)
@limiter.limit("5/hour")
async def register(request: Request, payload: RegisterIn, db: DbSession) -> RegisterOut:
    _ = request  # required by slowapi signature
    user = await auth_service.register_user(
        db,
        email=payload.email,
        password=payload.password,
        first_name=payload.first_name,
        last_name=payload.last_name,
    )
    return RegisterOut(user=UserPublic.from_model(user))


@router.post("/login", response_model=LoginOut)
@limiter.limit("20/hour")
async def login(
    request: Request, payload: LoginIn, response: Response, db: DbSession
) -> LoginOut:
    ua, ip = _client_meta(request)
    user, access, refresh_plain = await auth_service.authenticate(
        db, email=payload.email, password=payload.password, user_agent=ua, ip=ip
    )
    _set_refresh_cookie(response, refresh_plain)
    return LoginOut(access_token=access, user=UserPublic.from_model(user))


@router.post("/refresh", response_model=RefreshOut)
@limiter.limit("30/minute")
async def refresh(
    request: Request,
    response: Response,
    db: DbSession,
    refresh_token: str | None = Cookie(default=None, alias=REFRESH_COOKIE_NAME),
) -> RefreshOut:
    from app.exceptions import RefreshInvalid

    if not refresh_token:
        raise RefreshInvalid()
    ua, ip = _client_meta(request)
    _user, access, new_plain = await auth_service.rotate_refresh(
        db, refresh_plain=refresh_token, user_agent=ua, ip=ip
    )
    _set_refresh_cookie(response, new_plain)
    return RefreshOut(access_token=access)


@router.post("/logout", status_code=204)
async def logout(
    response: Response,
    db: DbSession,
    refresh_token: str | None = Cookie(default=None, alias=REFRESH_COOKIE_NAME),
) -> Response:
    await auth_service.logout(db, refresh_plain=refresh_token)
    _clear_refresh_cookie(response)
    response.status_code = 204
    return response


@router.post("/email/verify", response_model=EmailVerificationOut)
async def verify_email(payload: VerifyEmailIn, db: DbSession) -> EmailVerificationOut:
    user = await auth_service.verify_email(db, token_plain=payload.token)
    assert user.email_verified_at is not None
    return EmailVerificationOut(
        user=UserPublic.from_model(user), verified_at=user.email_verified_at
    )


@router.post("/email/resend-verification", status_code=204)
@limiter.limit("5/hour")
async def resend_verification(
    request: Request, user: CurrentUser, db: DbSession
) -> Response:
    _ = request  # required by slowapi signature
    await auth_service.resend_verification(db, user=user)
    return Response(status_code=204)
