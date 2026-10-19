"""Supervisor dashboard: real, database-backed metrics only."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import CurrentContext, require_any
from app.db.base import get_db
from app.schemas.dashboard import DashboardOut
from app.services import dashboard_service

router = APIRouter()


@router.get("", response_model=DashboardOut)
async def get_dashboard(
    context: CurrentContext = Depends(require_any),
    db: AsyncSession = Depends(get_db),
) -> DashboardOut:
    return await dashboard_service.get_dashboard(db, context.organization_id)
