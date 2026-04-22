"""Health endpoints."""

from __future__ import annotations

from fastapi import APIRouter
from sqlalchemy import text

from app.api.deps import DbSession

router = APIRouter()


@router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/health/deep")
async def health_deep(db: DbSession) -> dict:  # type: ignore[type-arg]
    checks: dict[str, str] = {}
    status = "ok"
    try:
        await db.execute(text("SELECT 1"))
        checks["postgres"] = "ok"
    except Exception:
        checks["postgres"] = "fail"
        status = "degraded"
    # TODO: redis and R2 checks land with their services.
    return {"status": status, "checks": checks}
