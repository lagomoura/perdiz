"""User upload endpoints (presign + commit) against MinIO.

Mirrors test_admin_uploads for the ``/v1/uploads/*`` surface. Requires
``current_verified_user``; unverified / anonymous requests get blocked.
"""

from __future__ import annotations

import struct
from datetime import UTC, datetime

import httpx
from app.db.session import AsyncSessionLocal
from app.models.media_file import MediaFile
from app.models.user import User
from httpx import AsyncClient
from sqlalchemy import select, update

from tests.integration._helpers import auth_header, register_user

# Tiny valid PNG: 1x1 pixel.
_PNG_1X1 = bytes.fromhex(
    "89504E470D0A1A0A0000000D49484452"
    "0000000100000001080600000000"
    "1F15C4890000000D4944415478DA63F8"
    "FFFFFF3F0000060002030100000000"
    "0000000049454E44AE426082"
)


def _make_binary_stl(triangles: int = 2) -> bytes:
    header = b"aura test stl".ljust(80, b"\x00")
    body = b"\x00" * (50 * triangles)
    return header + struct.pack("<I", triangles) + body


async def _verify_email(email: str) -> None:
    async with AsyncSessionLocal() as s:
        await s.execute(
            update(User).where(User.email == email).values(email_verified_at=datetime.now(tz=UTC))
        )
        await s.commit()


async def _register_and_verify(
    client: AsyncClient,
    *,
    email: str = "user@example.com",
) -> str:
    token = await register_user(client, email=email)
    await _verify_email(email)
    # Re-login so the access token reflects a verified state if needed.
    # The token payload itself doesn't carry email_verified; the dep fetches
    # the user by id on every request, so no re-login is strictly required.
    return token


async def _put_to_minio(url: str, body: bytes, content_type: str) -> None:
    async with httpx.AsyncClient(timeout=30) as http:
        r = await http.put(url, content=body, headers={"Content-Type": content_type})
        assert r.status_code in (200, 201), f"PUT failed: {r.status_code} {r.text}"


# --- AuthZ -----------------------------------------------------------------


async def test_anonymous_blocked(client: AsyncClient) -> None:
    r = await client.post(
        "/v1/uploads/presign",
        json={
            "kind": "user_upload_image",
            "mime_type": "image/png",
            "size_bytes": 64,
            "filename": "a.png",
        },
    )
    assert r.status_code == 401


async def test_unverified_user_blocked(client: AsyncClient) -> None:
    token = await register_user(client, email="unverified@example.com")
    r = await client.post(
        "/v1/uploads/presign",
        json={
            "kind": "user_upload_image",
            "mime_type": "image/png",
            "size_bytes": len(_PNG_1X1),
            "filename": "x.png",
        },
        headers=auth_header(token),
    )
    assert r.status_code == 403
    assert r.json()["error"]["code"] == "AUTH_EMAIL_NOT_VERIFIED"


# --- Happy paths -----------------------------------------------------------


async def test_user_image_full_flow(client: AsyncClient) -> None:
    token = await _register_and_verify(client)
    h = auth_header(token)

    presign = (
        await client.post(
            "/v1/uploads/presign",
            json={
                "kind": "user_upload_image",
                "mime_type": "image/png",
                "size_bytes": len(_PNG_1X1),
                "filename": "grabado.png",
            },
            headers=h,
        )
    ).json()
    assert presign["storage_key"].startswith("uploads/images/")

    await _put_to_minio(presign["upload_url"], _PNG_1X1, "image/png")

    commit = await client.post(
        "/v1/uploads/commit",
        json={
            "storage_key": presign["storage_key"],
            "kind": "user_upload_image",
            "mime_type": "image/png",
            "size_bytes": len(_PNG_1X1),
        },
        headers=h,
    )
    assert commit.status_code == 201, commit.text
    media = commit.json()["media_file"]
    assert media["kind"] == "user_upload_image"

    async with AsyncSessionLocal() as s:
        row = (await s.execute(select(MediaFile).where(MediaFile.id == media["id"]))).scalar_one()
        # owner_user_id is populated with the uploader.
        assert row.owner_user_id is not None


async def test_user_model_full_flow(client: AsyncClient) -> None:
    token = await _register_and_verify(client, email="modeluser@example.com")
    h = auth_header(token)
    stl = _make_binary_stl(triangles=10)
    presign = (
        await client.post(
            "/v1/uploads/presign",
            json={
                "kind": "user_upload_model",
                "mime_type": "model/stl",
                "size_bytes": len(stl),
                "filename": "mio.stl",
            },
            headers=h,
        )
    ).json()
    assert presign["storage_key"].startswith("uploads/models/")
    await _put_to_minio(presign["upload_url"], stl, "model/stl")

    commit = await client.post(
        "/v1/uploads/commit",
        json={
            "storage_key": presign["storage_key"],
            "kind": "user_upload_model",
            "mime_type": "model/stl",
            "size_bytes": len(stl),
        },
        headers=h,
    )
    assert commit.status_code == 201
    media = commit.json()["media_file"]
    assert media["kind"] == "user_upload_model"


# --- Rejections ------------------------------------------------------------


async def test_user_cannot_use_admin_kind(client: AsyncClient) -> None:
    """Submitting kind=image (admin-only) to the user endpoint should fail
    at the schema layer with 422 — the user router declares UserKind.
    """
    token = await _register_and_verify(client, email="admkind@example.com")
    r = await client.post(
        "/v1/uploads/presign",
        json={
            "kind": "image",  # admin-only
            "mime_type": "image/png",
            "size_bytes": len(_PNG_1X1),
            "filename": "x.png",
        },
        headers=auth_header(token),
    )
    assert r.status_code == 422
