"""Centralised settings. The app fails to start if required vars are missing."""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict

Env = Literal["development", "staging", "production"]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env", ".env.local"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # App
    app_env: Env = "development"
    app_debug: bool = False
    app_base_url: str = "http://localhost:8000"
    web_base_url: str = "http://localhost:5173"
    allowed_origins: str = "http://localhost:5173"

    # DB
    db_url: str
    db_pool_size: int = 10
    db_max_overflow: int = 20

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # JWT
    jwt_secret: str
    jwt_secret_next: str | None = None
    jwt_access_ttl_seconds: int = 900
    jwt_refresh_ttl_seconds: int = 1_209_600

    # OAuth
    oauth_google_client_id: str = ""
    oauth_google_client_secret: str = ""
    oauth_google_redirect_url: str = ""
    oauth_microsoft_client_id: str = ""
    oauth_microsoft_client_secret: str = ""
    oauth_microsoft_tenant: str = "common"
    oauth_microsoft_redirect_url: str = ""

    # R2 / S3
    r2_account_id: str = ""
    r2_access_key_id: str = ""
    r2_secret_access_key: str = ""
    r2_bucket: str = "aura-media"
    r2_public_base_url: str = ""
    r2_region: str = "auto"
    r2_endpoint_url: str = ""

    # Payments
    mercadopago_access_token: str = ""
    mercadopago_webhook_secret: str = ""
    stripe_secret_key: str = ""
    stripe_webhook_secret: str = ""
    paypal_client_id: str = ""
    paypal_client_secret: str = ""
    paypal_mode: Literal["sandbox", "live"] = "sandbox"

    # Email
    resend_api_key: str = ""
    email_from: str = "Aura <hola@aura.local>"
    email_support: str = "soporte@aura.local"

    # Observability
    sentry_dsn: str = ""
    sentry_traces_sample_rate: float = 0.0
    log_level: str = "INFO"

    # Admin bootstrap
    bootstrap_admin_email: str = ""
    bootstrap_admin_password: str = ""

    @property
    def allowed_origins_list(self) -> list[str]:
        return [o.strip() for o in self.allowed_origins.split(",") if o.strip()]


@lru_cache
def _get_settings() -> Settings:
    # Settings is populated entirely from env / .env files by pydantic-settings.
    return Settings()  # type: ignore[call-arg]


settings: Settings = _get_settings()
