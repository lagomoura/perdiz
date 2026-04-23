"""Admin coupon CRUD."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from app.db.session import AsyncSessionLocal
from app.models.audit_log import AuditLog
from app.models.coupon import Coupon
from httpx import AsyncClient
from sqlalchemy import select

from tests.integration._helpers import (
    auth_header,
    register_and_promote_admin,
    register_user,
)


def _payload(code: str = "V20", **overrides) -> dict:  # type: ignore[no-untyped-def]
    base = {
        "code": code,
        "type": "percentage",
        "value": 20,
        "min_order_cents": 0,
        "valid_from": None,
        "valid_until": None,
        "max_uses_total": None,
        "max_uses_per_user": None,
        "applicable_category_ids": [],
        "applicable_product_ids": [],
        "stacks_with_automatic": False,
        "status": "active",
    }
    base.update(overrides)
    return base


# --- AuthZ ---------------------------------------------------------------


async def test_anonymous_blocked(client: AsyncClient) -> None:
    r = await client.get("/v1/admin/coupons")
    assert r.status_code == 401


async def test_non_admin_blocked_with_404(client: AsyncClient) -> None:
    token = await register_user(client, email="u@example.com")
    r = await client.get("/v1/admin/coupons", headers=auth_header(token))
    assert r.status_code == 404


# --- CRUD happy path -----------------------------------------------------


async def test_create_list_and_get(client: AsyncClient) -> None:
    h = auth_header(await register_and_promote_admin(client))
    r = await client.post("/v1/admin/coupons", json=_payload("V20"), headers=h)
    assert r.status_code == 201
    created = r.json()["coupon"]
    assert created["code"] == "v20"  # normalized lowercase

    listing = await client.get("/v1/admin/coupons", headers=h)
    assert len(listing.json()["data"]) == 1

    detail = await client.get(f"/v1/admin/coupons/{created['id']}", headers=h)
    assert detail.status_code == 200


async def test_create_rejects_percentage_over_100(client: AsyncClient) -> None:
    h = auth_header(await register_and_promote_admin(client))
    r = await client.post(
        "/v1/admin/coupons",
        json=_payload("BIG", type="percentage", value=200),
        headers=h,
    )
    assert r.status_code == 422


async def test_create_rejects_bad_time_window(client: AsyncClient) -> None:
    h = auth_header(await register_and_promote_admin(client))
    now = datetime.now(tz=UTC)
    r = await client.post(
        "/v1/admin/coupons",
        json=_payload(
            "BADWIN",
            valid_from=(now + timedelta(days=5)).isoformat(),
            valid_until=now.isoformat(),
        ),
        headers=h,
    )
    assert r.status_code == 422


async def test_create_rejects_duplicate_code(client: AsyncClient) -> None:
    h = auth_header(await register_and_promote_admin(client))
    await client.post("/v1/admin/coupons", json=_payload("SAME"), headers=h)
    r = await client.post("/v1/admin/coupons", json=_payload("SAME"), headers=h)
    assert r.status_code == 409


async def test_create_rejects_bad_pattern(client: AsyncClient) -> None:
    h = auth_header(await register_and_promote_admin(client))
    r = await client.post("/v1/admin/coupons", json=_payload("inv code!"), headers=h)
    assert r.status_code == 422


# --- Update / delete -----------------------------------------------------


async def test_update_partial(client: AsyncClient) -> None:
    h = auth_header(await register_and_promote_admin(client))
    created = (await client.post("/v1/admin/coupons", json=_payload("UPD"), headers=h)).json()[
        "coupon"
    ]
    r = await client.patch(
        f"/v1/admin/coupons/{created['id']}",
        json={"value": 50, "status": "disabled"},
        headers=h,
    )
    assert r.status_code == 200
    body = r.json()["coupon"]
    assert body["value"] == 50
    assert body["status"] == "disabled"


async def test_delete(client: AsyncClient) -> None:
    h = auth_header(await register_and_promote_admin(client))
    created = (await client.post("/v1/admin/coupons", json=_payload("DEL"), headers=h)).json()[
        "coupon"
    ]
    r = await client.delete(f"/v1/admin/coupons/{created['id']}", headers=h)
    assert r.status_code == 204
    async with AsyncSessionLocal() as s:
        row = (
            await s.execute(select(Coupon).where(Coupon.id == created["id"]))
        ).scalar_one_or_none()
        assert row is None


# --- Filters -------------------------------------------------------------


async def test_list_filter_by_status(client: AsyncClient) -> None:
    h = auth_header(await register_and_promote_admin(client))
    await client.post("/v1/admin/coupons", json=_payload("ACT"), headers=h)
    await client.post(
        "/v1/admin/coupons",
        json=_payload("DIS", status="disabled"),
        headers=h,
    )
    r = await client.get("/v1/admin/coupons?status=active", headers=h)
    assert [c["code"] for c in r.json()["data"]] == ["act"]


# --- Audit ---------------------------------------------------------------


async def test_mutations_are_audited(client: AsyncClient) -> None:
    h = auth_header(await register_and_promote_admin(client))
    created = (await client.post("/v1/admin/coupons", json=_payload("AUD"), headers=h)).json()[
        "coupon"
    ]
    await client.patch(f"/v1/admin/coupons/{created['id']}", json={"value": 30}, headers=h)
    await client.delete(f"/v1/admin/coupons/{created['id']}", headers=h)

    async with AsyncSessionLocal() as s:
        rows = (
            (
                await s.execute(
                    select(AuditLog)
                    .where(AuditLog.entity_id == created["id"])
                    .order_by(AuditLog.created_at.asc())
                )
            )
            .scalars()
            .all()
        )
        assert [r.action for r in rows] == [
            "coupon.create",
            "coupon.update",
            "coupon.delete",
        ]
