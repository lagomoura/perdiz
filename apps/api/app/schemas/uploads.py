"""Upload schemas (presign + commit)."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)


AdminKind = Literal["image", "model_stl"]
UserKind = Literal["user_upload_image", "user_upload_model"]


class PresignIn(_Strict):
    kind: AdminKind
    mime_type: str = Field(min_length=3, max_length=120)
    size_bytes: int = Field(gt=0, le=200 * 1024 * 1024)
    filename: str = Field(min_length=1, max_length=200)


class UserPresignIn(_Strict):
    kind: UserKind
    mime_type: str = Field(min_length=3, max_length=120)
    size_bytes: int = Field(gt=0, le=200 * 1024 * 1024)
    filename: str = Field(min_length=1, max_length=200)


class PresignOut(_Strict):
    storage_key: str
    upload_url: str
    method: Literal["PUT"]
    headers: dict[str, str]
    expires_at: datetime


class CommitIn(_Strict):
    storage_key: str = Field(min_length=1, max_length=500)
    kind: AdminKind
    mime_type: str = Field(min_length=3, max_length=120)
    size_bytes: int = Field(gt=0, le=200 * 1024 * 1024)


class UserCommitIn(_Strict):
    storage_key: str = Field(min_length=1, max_length=500)
    kind: UserKind
    mime_type: str = Field(min_length=3, max_length=120)
    size_bytes: int = Field(gt=0, le=200 * 1024 * 1024)


class MediaFileOut(_Strict):
    id: str
    kind: str
    mime_type: str
    size_bytes: int
    storage_key: str
    public_url: str | None
    metadata: dict[str, object]


class CommitOut(_Strict):
    media_file: MediaFileOut
