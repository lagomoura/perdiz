"""Audit service — snapshot + log helpers used by admin flows.

Admin services call ``log_mutation`` after persisting a change. The log row
is written inside the same transaction; if the mutation rolls back, the log
rolls back too, which is what we want (no orphan audit entries).
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Any

from sqlalchemy import inspect
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.repositories import audit as audit_repo

_SCRUB_KEYS = {"password", "password_hash", "token", "token_hash", "secret"}


def snapshot(entity: Any) -> dict[str, Any] | None:
    """Return a JSON-safe dict of a SQLAlchemy model's column values.

    Sensitive keys are masked. Returns None if ``entity`` is None.
    """
    if entity is None:
        return None
    mapper = inspect(entity).mapper
    out: dict[str, Any] = {}
    for column in mapper.columns:
        value = getattr(entity, column.key)
        if column.key in _SCRUB_KEYS:
            out[column.key] = "***" if value is not None else None
        else:
            out[column.key] = _jsonify(value)
    return out


def _jsonify(value: Any) -> Any:
    if isinstance(value, datetime | date):
        return value.isoformat()
    if isinstance(value, list | tuple):
        return [_jsonify(v) for v in value]
    if isinstance(value, dict):
        return {k: _jsonify(v) for k, v in value.items()}
    return value


async def log_mutation(
    db: AsyncSession,
    *,
    actor: User | None,
    action: str,
    entity_type: str,
    entity_id: str | None,
    before: dict[str, Any] | None = None,
    after: dict[str, Any] | None = None,
    ip: str | None = None,
    user_agent: str | None = None,
) -> None:
    await audit_repo.append(
        db,
        actor_id=actor.id if actor else None,
        actor_role=actor.role if actor else None,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        before_json=before,
        after_json=after,
        ip=ip,
        user_agent=user_agent,
    )
