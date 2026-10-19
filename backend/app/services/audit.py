"""Audit trail helper. Records consequential actions.

Secrets are never stored; only identifiers and human-readable metadata.
"""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.incident import AuditLog


async def record_audit(
    db: AsyncSession,
    *,
    organization_id: uuid.UUID,
    actor_id: uuid.UUID | None,
    action: str,
    entity_type: str,
    entity_id: uuid.UUID | None = None,
    detail: dict[str, Any] | None = None,
) -> AuditLog:
    log = AuditLog(
        organization_id=organization_id,
        actor_id=actor_id,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        detail=detail,
    )
    db.add(log)
    await db.flush()
    return log


async def list_activity(
    db: AsyncSession,
    organization_id: uuid.UUID,
    *,
    entity_type: str | None = None,
    action: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[AuditLog], int]:
    conditions = [AuditLog.organization_id == organization_id]
    if entity_type:
        conditions.append(AuditLog.entity_type == entity_type)
    if action:
        conditions.append(AuditLog.action == action)
    total = await db.scalar(
        select(func.count()).select_from(AuditLog).where(*conditions)
    )
    rows = (
        await db.execute(
            select(AuditLog)
            .where(*conditions)
            .order_by(AuditLog.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
    ).scalars().all()
    return list(rows), int(total or 0)
