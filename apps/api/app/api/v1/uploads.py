"""User upload endpoints: presign + commit for customization-attached files.

Requires a verified user. Rate limited. The MediaFile row records
``owner_user_id = <current user>`` so the cleanup job can attribute
abandoned uploads later.
"""

from __future__ import annotations

from fastapi import APIRouter, Request

from app.api.deps import CurrentVerifiedUser, DbSession
from app.api.rate_limit import limiter
from app.models.media_file import MediaFile
from app.schemas.uploads import (
    CommitOut,
    MediaFileOut,
    PresignOut,
    UserCommitIn,
    UserPresignIn,
)
from app.services.media import uploads as uploads_service

router = APIRouter(prefix="/uploads", tags=["uploads"])


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
@limiter.limit("20/minute")
async def presign(
    request: Request,
    payload: UserPresignIn,
    _actor: CurrentVerifiedUser,
) -> PresignOut:
    _ = request  # required by slowapi
    result = await uploads_service.presign(
        kind=payload.kind,
        mime_type=payload.mime_type,
        size_bytes=payload.size_bytes,
        filename=payload.filename,
        allowed_kinds=uploads_service.USER_KINDS,
    )
    return PresignOut(
        storage_key=result.storage_key,
        upload_url=result.url,
        method=result.method,
        headers=result.headers,
        expires_at=result.expires_at,
    )


@router.post("/commit", response_model=CommitOut, status_code=201)
@limiter.limit("20/minute")
async def commit(
    request: Request,
    payload: UserCommitIn,
    db: DbSession,
    actor: CurrentVerifiedUser,
) -> CommitOut:
    _ = request  # required by slowapi
    media = await uploads_service.commit(
        db,
        actor=actor,
        storage_key=payload.storage_key,
        kind=payload.kind,
        declared_mime_type=payload.mime_type,
        declared_size_bytes=payload.size_bytes,
        allowed_kinds=uploads_service.USER_KINDS,
    )
    return CommitOut(media_file=_to_dto(media))
