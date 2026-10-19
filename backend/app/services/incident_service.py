"""Incident business logic with role-aware status transitions."""

from __future__ import annotations

import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import NotFoundError, PermissionDeniedError, ValidationAppError
from app.db.base import utcnow
from app.models.enums import IncidentStatus, Role
from app.models.incident import Incident
from app.schemas.incident import IncidentCreate, IncidentUpdate
from app.services.audit import record_audit

# Permitted incident status transitions (workflow guard).
INCIDENT_TRANSITIONS: dict[IncidentStatus, set[IncidentStatus]] = {
    IncidentStatus.open: {IncidentStatus.investigating, IncidentStatus.resolved, IncidentStatus.closed},
    IncidentStatus.investigating: {IncidentStatus.resolved, IncidentStatus.closed, IncidentStatus.open},
    IncidentStatus.resolved: {IncidentStatus.closed, IncidentStatus.investigating},
    IncidentStatus.closed: {IncidentStatus.investigating},
}


async def create_incident(
    db: AsyncSession,
    *,
    organization_id: uuid.UUID,
    reporter_id: uuid.UUID,
    payload: IncidentCreate,
) -> Incident:
    incident = Incident(
        organization_id=organization_id,
        title=payload.title.strip(),
        description=payload.description.strip(),
        machine=payload.machine,
        severity=payload.severity,
        reported_by=reporter_id,
    )
    db.add(incident)
    await db.flush()
    await record_audit(
        db,
        organization_id=organization_id,
        actor_id=reporter_id,
        action="incident.created",
        entity_type="incident",
        entity_id=incident.id,
        detail={"severity": payload.severity.value, "machine": payload.machine},
    )
    return incident


async def get_incident(
    db: AsyncSession, organization_id: uuid.UUID, incident_id: uuid.UUID
) -> Incident:
    incident = await db.scalar(
        select(Incident).where(
            Incident.id == incident_id,
            Incident.organization_id == organization_id,
        )
    )
    if incident is None:
        raise NotFoundError("Incident not found.")
    return incident


async def list_incidents(
    db: AsyncSession,
    organization_id: uuid.UUID,
    *,
    status: IncidentStatus | None = None,
    severity=None,
    machine: str | None = None,
    search: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[Incident], int]:
    conditions = [Incident.organization_id == organization_id]
    if status is not None:
        conditions.append(Incident.status == status)
    if severity is not None:
        conditions.append(Incident.severity == severity)
    if machine:
        conditions.append(Incident.machine.ilike(f"%{machine}%"))
    if search:
        like = f"%{search}%"
        conditions.append(Incident.title.ilike(like) | Incident.description.ilike(like))

    total = await db.scalar(
        select(func.count()).select_from(Incident).where(*conditions)
    )
    rows = (
        await db.execute(
            select(Incident)
            .where(*conditions)
            .order_by(Incident.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
    ).scalars().all()
    return list(rows), int(total or 0)


async def update_incident(
    db: AsyncSession,
    *,
    organization_id: uuid.UUID,
    actor_id: uuid.UUID,
    role: Role,
    incident: Incident,
    payload: IncidentUpdate,
) -> Incident:
    data = payload.model_dump(exclude_unset=True)

    new_status = data.get("status")
    if new_status is not None and new_status != incident.status:
        if role == Role.worker:
            raise PermissionDeniedError("Only supervisors can change incident status.")
        if new_status not in INCIDENT_TRANSITIONS.get(incident.status, set()):
            raise ValidationAppError(
                f"Cannot move incident from '{incident.status.value}' to '{new_status.value}'."
            )
        incident.status = new_status
        if new_status in (IncidentStatus.resolved, IncidentStatus.closed):
            incident.resolved_at = utcnow()
        elif new_status in (IncidentStatus.open, IncidentStatus.investigating):
            incident.resolved_at = None

    for field in ("title", "description", "machine", "severity", "resolution_notes"):
        if field in data and data[field] is not None:
            setattr(incident, field, data[field])

    await db.flush()
    await record_audit(
        db,
        organization_id=organization_id,
        actor_id=actor_id,
        action="incident.updated",
        entity_type="incident",
        entity_id=incident.id,
        detail={"status": incident.status.value, "fields": sorted(data.keys())},
    )
    return incident
