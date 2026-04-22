"""Users endpoints. Currently only /me; profile CRUD lands in a later PR."""

from __future__ import annotations

from fastapi import APIRouter

from app.api.deps import CurrentUser
from app.schemas.auth import MeOut, UserPublic

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=MeOut)
async def me(user: CurrentUser) -> MeOut:
    return MeOut(user=UserPublic.from_model(user))
