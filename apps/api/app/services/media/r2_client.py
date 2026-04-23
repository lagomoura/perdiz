"""Thin async wrapper around boto3 for R2 / MinIO access.

boto3 is sync by design. For the short-lived S3 operations we need (presign,
HEAD, Range GET), running them on the default executor via ``asyncio.to_thread``
keeps the code simple without pulling in aiobotocore. Measure before replacing.
"""

from __future__ import annotations

import asyncio
from functools import lru_cache
from typing import Any

import boto3
from botocore.client import Config as BotoConfig
from botocore.exceptions import ClientError

from app.config import settings


@lru_cache(maxsize=1)
def _s3_client() -> Any:
    """Singleton S3 client. boto3 clients are thread-safe per the docs,
    so sharing is safe. Endpoint URL drives MinIO vs. R2 choice.
    """
    kwargs: dict[str, Any] = {
        "aws_access_key_id": settings.r2_access_key_id,
        "aws_secret_access_key": settings.r2_secret_access_key,
        "region_name": settings.r2_region or "auto",
        "config": BotoConfig(
            signature_version="s3v4",
            # MinIO requires path-style addressing.
            s3={"addressing_style": "path"},
        ),
    }
    if settings.r2_endpoint_url:
        kwargs["endpoint_url"] = settings.r2_endpoint_url
    return boto3.client("s3", **kwargs)


async def generate_presigned_put_url(
    *, storage_key: str, content_type: str, content_length: int, expires_seconds: int = 600
) -> str:
    def _generate() -> str:
        client = _s3_client()
        url: str = client.generate_presigned_url(
            "put_object",
            Params={
                "Bucket": settings.r2_bucket,
                "Key": storage_key,
                "ContentType": content_type,
                "ContentLength": content_length,
            },
            ExpiresIn=expires_seconds,
        )
        return url

    return await asyncio.to_thread(_generate)


async def head_object(storage_key: str) -> dict[str, Any] | None:
    """Return HEAD metadata or None if the object is absent (NoSuchKey / 404)."""

    def _head() -> dict[str, Any] | None:
        client = _s3_client()
        try:
            response = client.head_object(Bucket=settings.r2_bucket, Key=storage_key)
        except ClientError as exc:
            code = exc.response.get("Error", {}).get("Code")
            if code in ("404", "NoSuchKey", "NotFound"):
                return None
            raise
        return {
            "content_length": int(response.get("ContentLength") or 0),
            "content_type": response.get("ContentType"),
            "etag": response.get("ETag"),
            "last_modified": response.get("LastModified"),
        }

    return await asyncio.to_thread(_head)


async def get_range(storage_key: str, *, start: int, end: int) -> bytes:
    """Download a byte range inclusive of both ends. Used for magic-bytes and
    STL header checks without fetching the full object.
    """

    def _get() -> bytes:
        client = _s3_client()
        response = client.get_object(
            Bucket=settings.r2_bucket,
            Key=storage_key,
            Range=f"bytes={start}-{end}",
        )
        body = response["Body"].read()
        assert isinstance(body, bytes)
        return body

    return await asyncio.to_thread(_get)


async def get_object(storage_key: str) -> bytes:
    """Download the full object body."""

    def _get() -> bytes:
        client = _s3_client()
        response = client.get_object(Bucket=settings.r2_bucket, Key=storage_key)
        body = response["Body"].read()
        assert isinstance(body, bytes)
        return body

    return await asyncio.to_thread(_get)


async def put_object(storage_key: str, data: bytes, *, content_type: str) -> None:
    """Upload ``data`` to R2 with the given content-type. Overwrites if present."""

    def _put() -> None:
        client = _s3_client()
        client.put_object(
            Bucket=settings.r2_bucket,
            Key=storage_key,
            Body=data,
            ContentType=content_type,
        )

    await asyncio.to_thread(_put)


async def delete_object(storage_key: str) -> None:
    def _delete() -> None:
        client = _s3_client()
        client.delete_object(Bucket=settings.r2_bucket, Key=storage_key)

    await asyncio.to_thread(_delete)
