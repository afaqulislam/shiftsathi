"""Incident endpoints. Any authenticated member may report; only supervisors
may change workflow status (enforced in the service layer).
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import CurrentContext, require_any
from app.db.base import get_db
from app.models.enums import IncidentStatus, Severity
from app.schemas.incident import (
    IncidentCreate,
    IncidentListOut,
    IncidentOut,
    IncidentUpdate,
)
from app.services import incident_service

router = APIRouter()


@router.get("", response_model=IncidentListOut)
async def list_incidents(
    status_filter: IncidentStatus | None = Query(default=None, alias="status"),
    severity: Severity | None = Query(default=None),
    machine: str | None = Query(default=None, max_length=200),
    search: str | None = Query(default=None, max_length=200),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    context: CurrentContext = Depends(require_any),
    db: AsyncSession = Depends(get_db),
) -> IncidentListOut:
    items, total = await incident_service.list_incidents(
        db,
        context.organization_id,
        status=status_filter,
        severity=severity,
        machine=machine,
        search=search,
        limit=limit,
        offset=offset,
    )
    return IncidentListOut(
        items=[IncidentOut.model_validate(i) for i in items],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.post("", response_model=IncidentOut, status_code=status.HTTP_201_CREATED)
async def create_incident(
    payload: IncidentCreate,
    context: CurrentContext = Depends(require_any),
    db: AsyncSession = Depends(get_db),
) -> IncidentOut:
    incident = await incident_service.create_incident(
        db,
        organization_id=context.organization_id,
        reporter_id=context.user_id,
        payload=payload,
    )
    await db.commit()
    return IncidentOut.model_validate(incident)


@router.get("/{incident_id}", response_model=IncidentOut)
async def get_incident(
    incident_id: uuid.UUID,
    context: CurrentContext = Depends(require_any),
    db: AsyncSession = Depends(get_db),
) -> IncidentOut:
    incident = await incident_service.get_incident(
        db, context.organization_id, incident_id
    )
    return IncidentOut.model_validate(incident)


@router.patch("/{incident_id}", response_model=IncidentOut)
async def update_incident(
    incident_id: uuid.UUID,
    payload: IncidentUpdate,
    context: CurrentContext = Depends(require_any),
    db: AsyncSession = Depends(get_db),
) -> IncidentOut:
    incident = await incident_service.get_incident(
        db, context.organization_id, incident_id
    )
    incident = await incident_service.update_incident(
        db,
        organization_id=context.organization_id,
        actor_id=context.user_id,
        role=context.role,
        incident=incident,
        payload=payload,
    )
    await db.commit()
    return IncidentOut.model_validate(incident)
