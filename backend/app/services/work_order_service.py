"""Work-order workflow, assignment, resolution and verification."""

from __future__ import annotations

import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import (
    NotFoundError,
    PermissionDeniedError,
    ValidationAppError,
)
from app.db.base import utcnow
from app.models.enums import (
    IncidentStatus,
    Priority,
    Role,
    WorkOrderStatus,
)
from app.models.incident import Incident, WorkOrder
from app.models.knowledge import VerifiedKnowledge
from app.models.org import Membership, User
from app.schemas.incident import WorkOrderCreate, WorkOrderUpdate
from app.services.ai.provider import AIProvider, get_ai_provider
from app.services.audit import record_audit

WORK_ORDER_TRANSITIONS: dict[WorkOrderStatus, set[WorkOrderStatus]] = {
    WorkOrderStatus.open: {
        WorkOrderStatus.assigned,
        WorkOrderStatus.in_progress,
        WorkOrderStatus.resolved,
        WorkOrderStatus.closed,
    },
    WorkOrderStatus.assigned: {
        WorkOrderStatus.in_progress,
        WorkOrderStatus.resolved,
        WorkOrderStatus.open,
    },
    WorkOrderStatus.in_progress: {
        WorkOrderStatus.resolved,
        WorkOrderStatus.assigned,
    },
    WorkOrderStatus.resolved: {
        WorkOrderStatus.closed,
        WorkOrderStatus.in_progress,
    },
    WorkOrderStatus.closed: {WorkOrderStatus.in_progress},
}

# Statuses a non-supervisor assignee may move a work order between.
WORKER_ALLOWED_STATUSES = {
    WorkOrderStatus.in_progress,
    WorkOrderStatus.resolved,
}


async def create_work_order(
    db: AsyncSession,
    *,
    organization_id: uuid.UUID,
    actor_id: uuid.UUID,
    payload: WorkOrderCreate,
) -> WorkOrder:
    incident: Incident | None = None
    if payload.incident_id is not None:
        incident = await db.scalar(
            select(Incident).where(
                Incident.id == payload.incident_id,
                Incident.organization_id == organization_id,
            )
        )
        if incident is None:
            raise NotFoundError("Incident not found.")

    if payload.assignee_id is not None:
        await _assert_member(db, organization_id, payload.assignee_id)

    status = (
        WorkOrderStatus.assigned
        if payload.assignee_id is not None
        else WorkOrderStatus.open
    )
    title = (payload.title or (incident.title if incident else "") or "").strip()
    if not title:
        raise ValidationAppError("A work-order title is required.")

    work_order = WorkOrder(
        organization_id=organization_id,
        incident_id=payload.incident_id,
        title=title[:300],
        description=(payload.description or (incident.description if incident else "")).strip(),
        machine=payload.machine or (incident.machine if incident else None),
        priority=payload.priority,
        status=status,
        assignee_id=payload.assignee_id,
        created_by=actor_id,
        due_date=payload.due_date,
    )
    db.add(work_order)
    await db.flush()

    # Populate the relationship in memory so serialising the freshly created
    # object never triggers an async lazy-load.
    if work_order.assignee_id:
        work_order.assignee = await db.get(User, work_order.assignee_id)

    await record_audit(
        db,
        organization_id=organization_id,
        actor_id=actor_id,
        action="work_order.created",
        entity_type="work_order",
        entity_id=work_order.id,
        detail={
            "priority": payload.priority.value,
            "incident_id": str(payload.incident_id) if payload.incident_id else None,
            "assignee_id": str(payload.assignee_id) if payload.assignee_id else None,
        },
    )
    return work_order


async def _assert_member(
    db: AsyncSession, organization_id: uuid.UUID, user_id: uuid.UUID
) -> None:
    exists = await db.scalar(
        select(Membership.id).where(
            Membership.organization_id == organization_id,
            Membership.user_id == user_id,
        )
    )
    if exists is None:
        raise ValidationAppError("Assignee must be a member of this workspace.")


async def get_work_order(
    db: AsyncSession, organization_id: uuid.UUID, work_order_id: uuid.UUID
) -> WorkOrder:
    wo = await db.scalar(
        select(WorkOrder).where(
            WorkOrder.id == work_order_id,
            WorkOrder.organization_id == organization_id,
        )
    )
    if wo is None:
        raise NotFoundError("Work order not found.")
    return wo


async def list_work_orders(
    db: AsyncSession,
    organization_id: uuid.UUID,
    *,
    status: WorkOrderStatus | None = None,
    priority: Priority | None = None,
    assignee_id: uuid.UUID | None = None,
    incident_id: uuid.UUID | None = None,
    machine: str | None = None,
    search: str | None = None,
    overdue_only: bool = False,
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[WorkOrder], int]:
    conditions = [WorkOrder.organization_id == organization_id]
    if status is not None:
        conditions.append(WorkOrder.status == status)
    else:
        conditions.append(WorkOrder.status != WorkOrderStatus.closed)
    if priority is not None:
        conditions.append(WorkOrder.priority == priority)
    if assignee_id is not None:
        conditions.append(WorkOrder.assignee_id == assignee_id)
    if incident_id is not None:
        conditions.append(WorkOrder.incident_id == incident_id)
    if machine:
        conditions.append(WorkOrder.machine.ilike(f"%{machine}%"))
    if search:
        like = f"%{search}%"
        conditions.append(WorkOrder.title.ilike(like) | WorkOrder.description.ilike(like))
    if overdue_only:
        conditions.append(WorkOrder.due_date.is_not(None))
        conditions.append(WorkOrder.due_date < func.now())
        conditions.append(
            WorkOrder.status.in_([WorkOrderStatus.open, WorkOrderStatus.assigned, WorkOrderStatus.in_progress])
        )

    total = await db.scalar(
        select(func.count()).select_from(WorkOrder).where(*conditions)
    )
    rows = (
        await db.execute(
            select(WorkOrder)
            .where(*conditions)
            .order_by(
                WorkOrder.due_date.asc().nulls_last(),
                WorkOrder.created_at.desc(),
            )
            .limit(limit)
            .offset(offset)
        )
    ).scalars().all()
    return list(rows), int(total or 0)


async def update_work_order(
    db: AsyncSession,
    *,
    organization_id: uuid.UUID,
    actor_id: uuid.UUID,
    role: Role,
    work_order: WorkOrder,
    payload: WorkOrderUpdate,
) -> WorkOrder:
    if role == Role.worker and work_order.assignee_id != actor_id:
        raise PermissionDeniedError(
            "Workers can only update work orders assigned to them."
        )
    data = payload.model_dump(exclude_unset=True)

    if "assignee_id" in data and data["assignee_id"] is not None:
        if role == Role.worker:
            raise PermissionDeniedError("Only supervisors can reassign work orders.")
        await _assert_member(db, organization_id, data["assignee_id"])
        work_order.assignee_id = data["assignee_id"]
        # Keep the in-memory relationship in sync so the response serialises
        # the new assignee without triggering an async lazy-load.
        work_order.assignee = await db.get(User, data["assignee_id"])
        if work_order.status == WorkOrderStatus.open:
            work_order.status = WorkOrderStatus.assigned

    for field in ("title", "description", "machine", "priority", "due_date", "resolution_notes"):
        if field in data:
            setattr(work_order, field, data[field])

    await db.flush()
    await record_audit(
        db,
        organization_id=organization_id,
        actor_id=actor_id,
        action="work_order.updated",
        entity_type="work_order",
        entity_id=work_order.id,
        detail={"fields": sorted(data.keys())},
    )
    return work_order


async def change_status(
    db: AsyncSession,
    *,
    organization_id: uuid.UUID,
    actor_id: uuid.UUID,
    role: Role,
    work_order: WorkOrder,
    new_status: WorkOrderStatus,
    resolution_notes: str | None,
) -> WorkOrder:
    if new_status == work_order.status:
        raise ValidationAppError(f"Work order is already '{new_status.value}'.")

    if role == Role.worker:
        if work_order.assignee_id != actor_id:
            raise PermissionDeniedError(
                "Workers can only update work orders assigned to them."
            )
        if new_status not in WORKER_ALLOWED_STATUSES:
            raise PermissionDeniedError(
                "Workers can only start or resolve their work orders."
            )

    if new_status not in WORK_ORDER_TRANSITIONS.get(work_order.status, set()):
        raise ValidationAppError(
            f"Cannot move work order from '{work_order.status.value}' to '{new_status.value}'."
        )

    if new_status == WorkOrderStatus.resolved and not (
        resolution_notes or work_order.resolution_notes
    ):
        raise ValidationAppError(
            "Resolution notes are required before a work order can be resolved."
        )

    work_order.status = new_status
    if resolution_notes:
        work_order.resolution_notes = resolution_notes
    if new_status == WorkOrderStatus.resolved:
        work_order.resolved_at = utcnow()
    elif new_status == WorkOrderStatus.closed:
        work_order.closed_at = utcnow()
    else:
        work_order.resolved_at = None

    # Verification only holds for a settled, human-approved resolution.
    # Any status other than closing (i.e. a new or reopened resolution)
    # revokes it so it must be reviewed again.
    if new_status != WorkOrderStatus.closed:
        work_order.is_verified = False
        work_order.verified_by = None
        work_order.verified_at = None

    # Keep the parent incident status in sync when the work order resolves.
    if work_order.incident_id and new_status in (
        WorkOrderStatus.resolved,
        WorkOrderStatus.closed,
    ):
        incident = await db.get(Incident, work_order.incident_id)
        if incident and incident.status in (
            IncidentStatus.open,
            IncidentStatus.investigating,
        ):
            incident.status = IncidentStatus.resolved
            incident.resolved_at = utcnow()

    await db.flush()
    await record_audit(
        db,
        organization_id=organization_id,
        actor_id=actor_id,
        action="work_order.status_changed",
        entity_type="work_order",
        entity_id=work_order.id,
        detail={"status": new_status.value},
    )
    return work_order


async def verify_work_order(
    db: AsyncSession,
    *,
    organization_id: uuid.UUID,
    actor_id: uuid.UUID,
    actor_role: Role,
    work_order: WorkOrder,
    verified: bool,
    provider: AIProvider | None = None,
) -> tuple[WorkOrder, VerifiedKnowledge | None]:
    """Human approval of a resolution. Only supervisor/admin may verify.

    On approval the resolution becomes searchable verified knowledge (with an
    embedding). Rejecting simply clears the verification flag.
    """
    if actor_role not in (Role.admin, Role.supervisor):
        raise PermissionDeniedError("Only supervisors can verify resolutions.")
    if work_order.status not in (WorkOrderStatus.resolved, WorkOrderStatus.closed):
        raise ValidationAppError("Only resolved work orders can be verified.")
    if not work_order.resolution_notes:
        raise ValidationAppError("This work order has no resolution notes to verify.")

    work_order.is_verified = verified
    work_order.verified_by = actor_id if verified else None
    work_order.verified_at = utcnow() if verified else None
    await db.flush()

    knowledge: VerifiedKnowledge | None = None
    if verified:
        content_parts = [f"Problem: {work_order.title}"]
        if work_order.machine:
            content_parts.append(f"Machine: {work_order.machine}")
        if work_order.description:
            content_parts.append(f"Details: {work_order.description}")
        content_parts.append(f"Verified resolution: {work_order.resolution_notes}")
        content = "\n".join(content_parts)

        provider = provider or get_ai_provider()
        vector = (await provider.embed([content]))[0]

        existing = await db.scalar(
            select(VerifiedKnowledge).where(
                VerifiedKnowledge.work_order_id == work_order.id
            )
        )
        if existing is not None:
            existing.title = work_order.title
            existing.machine = work_order.machine
            existing.content = content
            existing.embedding = vector
            existing.approved_by = actor_id
            existing.approved_at = utcnow()
            knowledge = existing
        else:
            knowledge = VerifiedKnowledge(
                organization_id=organization_id,
                work_order_id=work_order.id,
                incident_id=work_order.incident_id,
                title=work_order.title,
                machine=work_order.machine,
                content=content,
                embedding=vector,
                approved_by=actor_id,
            )
            db.add(knowledge)
        await db.flush()

    await record_audit(
        db,
        organization_id=organization_id,
        actor_id=actor_id,
        action="work_order.verified" if verified else "work_order.verification_revoked",
        entity_type="work_order",
        entity_id=work_order.id,
        detail={"verified": verified},
    )
    return work_order, knowledge


async def list_verified_knowledge(
    db: AsyncSession,
    organization_id: uuid.UUID,
    *,
    search: str | None = None,
    machine: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[VerifiedKnowledge], int]:
    conditions = [VerifiedKnowledge.organization_id == organization_id]
    if search:
        like = f"%{search}%"
        conditions.append(
            VerifiedKnowledge.title.ilike(like)
            | VerifiedKnowledge.content.ilike(like)
        )
    if machine:
        conditions.append(VerifiedKnowledge.machine.ilike(f"%{machine}%"))

    total = await db.scalar(
        select(func.count()).select_from(VerifiedKnowledge).where(*conditions)
    )
    rows = (
        await db.execute(
            select(VerifiedKnowledge)
            .where(*conditions)
            .order_by(VerifiedKnowledge.approved_at.desc())
            .limit(limit)
            .offset(offset)
        )
    ).scalars().all()
    return list(rows), int(total or 0)


async def get_verified_knowledge(
    db: AsyncSession, organization_id: uuid.UUID, knowledge_id: uuid.UUID
) -> VerifiedKnowledge:
    item = await db.scalar(
        select(VerifiedKnowledge).where(
            VerifiedKnowledge.id == knowledge_id,
            VerifiedKnowledge.organization_id == organization_id,
        )
    )
    if item is None:
        raise NotFoundError("Verified knowledge entry not found.")
    return item


async def count_pending_approvals(db: AsyncSession, organization_id: uuid.UUID) -> int:
    total = await db.scalar(
        select(func.count())
        .select_from(WorkOrder)
        .where(
            WorkOrder.organization_id == organization_id,
            WorkOrder.status == WorkOrderStatus.resolved,
            WorkOrder.is_verified.is_(False),
        )
    )
    return int(total or 0)


async def count_active(db: AsyncSession, organization_id: uuid.UUID) -> int:
    total = await db.scalar(
        select(func.count())
        .select_from(WorkOrder)
        .where(
            WorkOrder.organization_id == organization_id,
            WorkOrder.status.in_(
                [
                    WorkOrderStatus.open,
                    WorkOrderStatus.assigned,
                    WorkOrderStatus.in_progress,
                ]
            ),
        )
    )
    return int(total or 0)


async def count_overdue(db: AsyncSession, organization_id: uuid.UUID) -> int:
    total = await db.scalar(
        select(func.count())
        .select_from(WorkOrder)
        .where(
            WorkOrder.organization_id == organization_id,
            WorkOrder.due_date.is_not(None),
            WorkOrder.due_date < func.now(),
            WorkOrder.status.in_(
                [
                    WorkOrderStatus.open,
                    WorkOrderStatus.assigned,
                    WorkOrderStatus.in_progress,
                ]
            ),
        )
    )
    return int(total or 0)
