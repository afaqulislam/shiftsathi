"""Verified knowledge endpoints (human-approved resolutions)."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import CurrentContext, require_any
from app.db.base import get_db
from app.schemas.knowledge import VerifiedKnowledgeListOut, VerifiedKnowledgeOut
from app.services import work_order_service

router = APIRouter()


@router.get("", response_model=VerifiedKnowledgeListOut)
async def list_verified_knowledge(
    search: str | None = Query(default=None, max_length=200),
    machine: str | None = Query(default=None, max_length=200),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    context: CurrentContext = Depends(require_any),
    db: AsyncSession = Depends(get_db),
) -> VerifiedKnowledgeListOut:
    items, total = await work_order_service.list_verified_knowledge(
        db,
        context.organization_id,
        search=search,
        machine=machine,
        limit=limit,
        offset=offset,
    )
    return VerifiedKnowledgeListOut(
        items=[VerifiedKnowledgeOut.model_validate(i) for i in items],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/{knowledge_id}", response_model=VerifiedKnowledgeOut)
async def get_verified_knowledge(
    knowledge_id: uuid.UUID,
    context: CurrentContext = Depends(require_any),
    db: AsyncSession = Depends(get_db),
) -> VerifiedKnowledgeOut:
    item = await work_order_service.get_verified_knowledge(
        db, context.organization_id, knowledge_id
    )
    return VerifiedKnowledgeOut.model_validate(item)
