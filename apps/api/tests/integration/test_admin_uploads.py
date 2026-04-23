"""Admin upload endpoints against the MinIO instance from compose dev.

These tests exercise the full presign → PUT-to-S3 → commit loop with real
HTTP calls against MinIO. The compose setup seeds a public-read bucket
named ``perdiz-media`` before the API starts.
"""

from __future__ import annotations

import struct

import httpx
import pytest
from app.db.session import AsyncSessionLocal
from app.models.audit_log import AuditLog
from app.models.media_file import MediaFile
from app.services.media import r2_client
from httpx import AsyncClient
from sqlalchemy import select

from tests.integration._helpers import (
    auth_header,
    register_and_promote_admin,
    register_user,
)

# --- Fixtures / helpers -----------------------------------------------------


# Tiny valid PNG: 1x1 pixel.
_PNG_1X1 = bytes.fromhex(
    "89504E470D0A1A0A0000000D49484452"
    "0000000100000001080600000000"
    "1F15C4890000000D4944415478DA63F8"
    "FFFFFF3F0000060002030100000000"
    "0000000049454E44AE426082"
)

# Tiny valid JPEG (SOI + APP0 + SOS + EOI); enough to pass magic-bytes check.
_JPEG_HEADER = bytes.fromhex("FFD8FFE000104A46494600010100000100010000")
_JPEG_MIN = _JPEG_HEADER + b"\x00" * 64 + b"\xff\xd9"


def _make_binary_stl(triangles: int = 2) -> bytes:
    """Return a minimal valid-looking binary STL of ``triangles`` triangles.

    Each triangle is 50 bytes (12 floats * 4 bytes + 2 byte attribute count).
    Header is 80 bytes + 4-byte little-endian triangle count.
    """
    header = b"p3rdiz test stl".ljust(80, b"\x00")
    body = b"\x00" * (50 * triangles)
    return header + struct.pack("<I", triangles) + body


async def _put_to_minio(url: str, body: bytes, content_type: str) -> None:
    async with httpx.AsyncClient(timeout=30) as http:
        r = await http.put(url, content=body, headers={"Content-Type": content_type})
        assert r.status_code in (200, 201), f"PUT failed: {r.status_code} {r.text}"


@pytest.fixture(autouse=True)
def _reset_r2_client_cache() -> None:
    # The lru_cache on the S3 client is fine across tests, but clear it between
    # tests so any test that monkeypatches settings picks up the new values.
    r2_client._s3_client.cache_clear()


# --- Auth / happy paths -----------------------------------------------------


async def test_anon_and_non_admin_blocked(client: AsyncClient) -> None:
    r = await client.post("/v1/admin/uploads/presign", json={})
    assert r.status_code == 401

    token = await register_user(client)
    r = await client.post(
        "/v1/admin/uploads/presign",
        json={
            "kind": "image",
            "mime_type": "image/png",
            "size_bytes": len(_PNG_1X1),
            "filename": "a.png",
        },
        headers=auth_header(token),
    )
    assert r.status_code == 404


async def test_image_full_flow_png(client: AsyncClient) -> None:
    h = auth_header(await register_and_promote_admin(client))

    presign = await client.post(
        "/v1/admin/uploads/presign",
        json={
            "kind": "image",
            "mime_type": "image/png",
            "size_bytes": len(_PNG_1X1),
            "filename": "foto principal.png",
        },
        headers=h,
    )
    assert presign.status_code == 200, presign.text
    body = presign.json()
    assert body["method"] == "PUT"
    assert body["storage_key"].startswith("images/")
    assert body["storage_key"].endswith(".png")
    # Filename got sanitized (no spaces in storage_key).
    assert " " not in body["storage_key"]

    await _put_to_minio(body["upload_url"], _PNG_1X1, "image/png")

    commit = await client.post(
        "/v1/admin/uploads/commit",
        json={
            "storage_key": body["storage_key"],
            "kind": "image",
            "mime_type": "image/png",
            "size_bytes": len(_PNG_1X1),
        },
        headers=h,
    )
    assert commit.status_code == 201, commit.text
    media = commit.json()["media_file"]
    assert media["kind"] == "image"
    assert media["mime_type"] == "image/png"
    assert media["size_bytes"] == len(_PNG_1X1)
    assert media["storage_key"] == body["storage_key"]

    # MediaFile row persisted.
    async with AsyncSessionLocal() as s:
        row = (await s.execute(select(MediaFile).where(MediaFile.id == media["id"]))).scalar_one()
        assert row.kind == "image"
        assert row.storage_key == body["storage_key"]


async def test_image_full_flow_jpeg(client: AsyncClient) -> None:
    h = auth_header(await register_and_promote_admin(client))
    presign_body = (
        await client.post(
            "/v1/admin/uploads/presign",
            json={
                "kind": "image",
                "mime_type": "image/jpeg",
                "size_bytes": len(_JPEG_MIN),
                "filename": "pic.jpg",
            },
            headers=h,
        )
    ).json()
    await _put_to_minio(presign_body["upload_url"], _JPEG_MIN, "image/jpeg")
    commit = await client.post(
        "/v1/admin/uploads/commit",
        json={
            "storage_key": presign_body["storage_key"],
            "kind": "image",
            "mime_type": "image/jpeg",
            "size_bytes": len(_JPEG_MIN),
        },
        headers=h,
    )
    assert commit.status_code == 201


async def test_stl_full_flow(client: AsyncClient) -> None:
    h = auth_header(await register_and_promote_admin(client))
    stl = _make_binary_stl(triangles=100)
    presign_body = (
        await client.post(
            "/v1/admin/uploads/presign",
            json={
                "kind": "model_stl",
                "mime_type": "model/stl",
                "size_bytes": len(stl),
                "filename": "perdiz.stl",
            },
            headers=h,
        )
    ).json()
    assert presign_body["storage_key"].startswith("models/stl/")
    await _put_to_minio(presign_body["upload_url"], stl, "model/stl")

    commit = await client.post(
        "/v1/admin/uploads/commit",
        json={
            "storage_key": presign_body["storage_key"],
            "kind": "model_stl",
            "mime_type": "model/stl",
            "size_bytes": len(stl),
        },
        headers=h,
    )
    assert commit.status_code == 201, commit.text
    media = commit.json()["media_file"]
    assert media["kind"] == "model_stl"
    assert media["metadata"]["format"] == "binary"
    assert media["metadata"]["triangles"] == 100


# --- Negative paths ---------------------------------------------------------


async def test_presign_rejects_unsupported_mime_for_image(client: AsyncClient) -> None:
    h = auth_header(await register_and_promote_admin(client))
    r = await client.post(
        "/v1/admin/uploads/presign",
        json={
            "kind": "image",
            "mime_type": "image/gif",
            "size_bytes": 1000,
            "filename": "x.gif",
        },
        headers=h,
    )
    assert r.status_code == 422
    assert r.json()["error"]["code"] == "VALIDATION_ERROR"


async def test_presign_rejects_oversize_image(client: AsyncClient) -> None:
    h = auth_header(await register_and_promote_admin(client))
    r = await client.post(
        "/v1/admin/uploads/presign",
        json={
            "kind": "image",
            "mime_type": "image/png",
            "size_bytes": 6 * 1024 * 1024,  # 6 MB > 5 MB cap
            "filename": "huge.png",
        },
        headers=h,
    )
    assert r.status_code == 422


async def test_commit_rejects_missing_object(client: AsyncClient) -> None:
    h = auth_header(await register_and_promote_admin(client))
    r = await client.post(
        "/v1/admin/uploads/commit",
        json={
            "storage_key": "images/01HWFAKE/nonexistent.png",
            "kind": "image",
            "mime_type": "image/png",
            "size_bytes": 1000,
        },
        headers=h,
    )
    assert r.status_code == 422
    assert r.json()["error"]["code"] == "VALIDATION_ERROR"


async def test_commit_rejects_mime_mismatch_with_content(
    client: AsyncClient,
) -> None:
    h = auth_header(await register_and_promote_admin(client))
    presign_body = (
        await client.post(
            "/v1/admin/uploads/presign",
            json={
                "kind": "image",
                "mime_type": "image/png",
                "size_bytes": 64,
                "filename": "a.png",
            },
            headers=h,
        )
    ).json()
    # Upload JPEG bytes but declare PNG: magic-bytes check should fail.
    fake = _JPEG_HEADER + b"\x00" * (64 - len(_JPEG_HEADER))
    await _put_to_minio(presign_body["upload_url"], fake, "image/png")
    r = await client.post(
        "/v1/admin/uploads/commit",
        json={
            "storage_key": presign_body["storage_key"],
            "kind": "image",
            "mime_type": "image/png",
            "size_bytes": 64,
        },
        headers=h,
    )
    assert r.status_code == 422
    assert r.json()["error"]["code"] == "VALIDATION_ERROR"


async def test_commit_rejects_size_mismatch(client: AsyncClient) -> None:
    h = auth_header(await register_and_promote_admin(client))
    presign_body = (
        await client.post(
            "/v1/admin/uploads/presign",
            json={
                "kind": "image",
                "mime_type": "image/png",
                "size_bytes": len(_PNG_1X1),
                "filename": "a.png",
            },
            headers=h,
        )
    ).json()
    await _put_to_minio(presign_body["upload_url"], _PNG_1X1, "image/png")
    # Lie about the size at commit.
    r = await client.post(
        "/v1/admin/uploads/commit",
        json={
            "storage_key": presign_body["storage_key"],
            "kind": "image",
            "mime_type": "image/png",
            "size_bytes": len(_PNG_1X1) + 1,
        },
        headers=h,
    )
    assert r.status_code == 422


async def test_commit_rejects_corrupt_stl(client: AsyncClient) -> None:
    h = auth_header(await register_and_promote_admin(client))
    # Binary STL-like blob but with a triangle count that doesn't match the
    # file size. Header says "billions of triangles" but file is tiny.
    header = b"bogus".ljust(80, b"\x00") + struct.pack("<I", 10_000_000)
    body = header + b"\x00" * 100  # way too small for 10M triangles
    presign_body = (
        await client.post(
            "/v1/admin/uploads/presign",
            json={
                "kind": "model_stl",
                "mime_type": "model/stl",
                "size_bytes": len(body),
                "filename": "bad.stl",
            },
            headers=h,
        )
    ).json()
    await _put_to_minio(presign_body["upload_url"], body, "model/stl")
    r = await client.post(
        "/v1/admin/uploads/commit",
        json={
            "storage_key": presign_body["storage_key"],
            "kind": "model_stl",
            "mime_type": "model/stl",
            "size_bytes": len(body),
        },
        headers=h,
    )
    assert r.status_code == 422


# --- Audit ------------------------------------------------------------------


async def test_stl_commit_enqueues_conversion(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """After a successful STL commit, the admin flow hands the id off to the
    STL→GLB conversion queue. We patch the helper and assert the call; the
    queue/worker mechanics are covered by ``test_stl_to_glb``.
    """
    calls: list[str] = []

    async def _spy(media_file_id: str) -> None:
        calls.append(media_file_id)

    monkeypatch.setattr("app.services.media.uploads.media_queue.enqueue_stl_conversion", _spy)

    h = auth_header(await register_and_promote_admin(client))
    stl = _make_binary_stl(triangles=10)
    presign_body = (
        await client.post(
            "/v1/admin/uploads/presign",
            json={
                "kind": "model_stl",
                "mime_type": "model/stl",
                "size_bytes": len(stl),
                "filename": "enqueue.stl",
            },
            headers=h,
        )
    ).json()
    await _put_to_minio(presign_body["upload_url"], stl, "model/stl")

    commit = await client.post(
        "/v1/admin/uploads/commit",
        json={
            "storage_key": presign_body["storage_key"],
            "kind": "model_stl",
            "mime_type": "model/stl",
            "size_bytes": len(stl),
        },
        headers=h,
    )
    assert commit.status_code == 201
    media_id = commit.json()["media_file"]["id"]
    assert calls == [media_id]


async def test_image_commit_does_not_enqueue_conversion(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls: list[str] = []

    async def _spy(media_file_id: str) -> None:
        calls.append(media_file_id)

    monkeypatch.setattr("app.services.media.uploads.media_queue.enqueue_stl_conversion", _spy)

    h = auth_header(await register_and_promote_admin(client))
    presign_body = (
        await client.post(
            "/v1/admin/uploads/presign",
            json={
                "kind": "image",
                "mime_type": "image/png",
                "size_bytes": len(_PNG_1X1),
                "filename": "a.png",
            },
            headers=h,
        )
    ).json()
    await _put_to_minio(presign_body["upload_url"], _PNG_1X1, "image/png")
    commit = await client.post(
        "/v1/admin/uploads/commit",
        json={
            "storage_key": presign_body["storage_key"],
            "kind": "image",
            "mime_type": "image/png",
            "size_bytes": len(_PNG_1X1),
        },
        headers=h,
    )
    assert commit.status_code == 201
    assert calls == []


async def test_commit_is_audited(client: AsyncClient) -> None:
    h = auth_header(await register_and_promote_admin(client))
    presign_body = (
        await client.post(
            "/v1/admin/uploads/presign",
            json={
                "kind": "image",
                "mime_type": "image/png",
                "size_bytes": len(_PNG_1X1),
                "filename": "a.png",
            },
            headers=h,
        )
    ).json()
    await _put_to_minio(presign_body["upload_url"], _PNG_1X1, "image/png")
    commit = (
        await client.post(
            "/v1/admin/uploads/commit",
            json={
                "storage_key": presign_body["storage_key"],
                "kind": "image",
                "mime_type": "image/png",
                "size_bytes": len(_PNG_1X1),
            },
            headers=h,
        )
    ).json()
    media_id = commit["media_file"]["id"]
    async with AsyncSessionLocal() as s:
        rows = (
            (await s.execute(select(AuditLog).where(AuditLog.entity_id == media_id)))
            .scalars()
            .all()
        )
        assert [r.action for r in rows] == ["media_file.create.image"]
        assert rows[0].actor_role == "admin"
