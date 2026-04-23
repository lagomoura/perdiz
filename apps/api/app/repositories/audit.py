"""Audit log repository — append-only."""

from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit_log import AuditLog


async def append(
    db: AsyncSession,
    *,
    actor_id: str | None,
    actor_role: str | None,
    action: str,
    entity_type: str,
    entity_id: str | None,
    before_json: dict[str, Any] | None,
    after_json: dict[str, Any] | None,
    ip: str | None = None,
    user_agent: str | None = None,
) -> AuditLog:
    entry = AuditLog(
        actor_id=actor_id,
        actor_role=actor_role,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        before_json=before_json,
        after_json=after_json,
        ip=ip,
        user_agent=user_agent,
    )
    db.add(entry)
    await db.flush()
    return entry
