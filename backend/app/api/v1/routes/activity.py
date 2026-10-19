"""Activity feed endpoint (organization-scoped audit trail)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import CurrentContext, require_any
from app.db.base import get_db
from app.schemas.activity import ActivityListOut
from app.schemas.incident import AuditLogOut
from app.services import audit

router = APIRouter()


@router.get("", response_model=ActivityListOut)
async def list_activity(
    entity_type: str | None = Query(default=None, max_length=100),
    action: str | None = Query(default=None, max_length=100),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    context: CurrentContext = Depends(require_any),
    db: AsyncSession = Depends(get_db),
) -> ActivityListOut:
    items, total = await audit.list_activity(
        db,
        context.organization_id,
        entity_type=entity_type,
        action=action,
        limit=limit,
        offset=offset,
    )
    return ActivityListOut(
        items=[AuditLogOut.model_validate(i) for i in items],
        total=total,
        limit=limit,
        offset=offset,
    )
