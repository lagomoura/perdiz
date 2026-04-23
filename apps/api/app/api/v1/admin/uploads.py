"""Admin upload endpoints: presign + commit."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends

from app.api.deps import DbSession, require_role
from app.models.media_file import MediaFile
from app.models.user import User
from app.schemas.uploads import (
    CommitIn,
    CommitOut,
    MediaFileOut,
    PresignIn,
    PresignOut,
)
from app.services.media import uploads as uploads_service

router = APIRouter(
    prefix="/admin/uploads",
    tags=["admin-uploads"],
    dependencies=[Depends(require_role("admin"))],
)


def _to_dto(media: MediaFile) -> MediaFileOut:
    return MediaFileOut(
        id=media.id,
        kind=media.kind,
        mime_type=media.mime_type,
        size_bytes=media.size_bytes,
        storage_key=media.storage_key,
        public_url=media.public_url,
        metadata=media.file_metadata or {},
    )


@router.post("/presign", response_model=PresignOut)
async def presign(
    payload: PresignIn,
    _actor: Annotated[User, Depends(require_role("admin"))],
) -> PresignOut:
    result = await uploads_service.presign(
        kind=payload.kind,
        mime_type=payload.mime_type,
        size_bytes=payload.size_bytes,
        filename=payload.filename,
    )
    return PresignOut(
        storage_key=result.storage_key,
        upload_url=result.url,
        method=result.method,
        headers=result.headers,
        expires_at=result.expires_at,
    )


@router.post("/commit", response_model=CommitOut, status_code=201)
async def commit(
    payload: CommitIn,
    db: DbSession,
    actor: Annotated[User, Depends(require_role("admin"))],
) -> CommitOut:
    media = await uploads_service.commit(
        db,
        actor=actor,
        storage_key=payload.storage_key,
        kind=payload.kind,
        declared_mime_type=payload.mime_type,
        declared_size_bytes=payload.size_bytes,
    )
    return CommitOut(media_file=_to_dto(media))
