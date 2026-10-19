"""Database-backed dashboard metrics. No fabricated numbers."""

from __future__ import annotations

import datetime as dt
import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document import Document
from app.models.enums import (
    DocumentStatus,
    IncidentStatus,
    Severity,
    WorkOrderStatus,
)
from app.models.incident import AuditLog, Incident, WorkOrder
from app.models.knowledge import VerifiedKnowledge
from app.schemas.dashboard import (
    DashboardMetrics,
    DashboardOut,
    DocumentStatusCounts,
)
from app.schemas.incident import AuditLogOut, IncidentOut, WorkOrderOut
from app.services.work_order_service import count_overdue, count_pending_approvals


async def _count(db: AsyncSession, model, *conditions) -> int:
    total = await db.scalar(select(func.count()).select_from(model).where(*conditions))
    return int(total or 0)


async def get_dashboard(
    db: AsyncSession, organization_id: uuid.UUID
) -> DashboardOut:
    open_incidents = await _count(
        db,
        Incident,
        Incident.organization_id == organization_id,
        Incident.status.in_([IncidentStatus.open, IncidentStatus.investigating]),
    )
    active_work_orders = await _count(
        db,
        WorkOrder,
        WorkOrder.organization_id == organization_id,
        WorkOrder.status.in_(
            [
                WorkOrderStatus.open,
                WorkOrderStatus.assigned,
                WorkOrderStatus.in_progress,
            ]
        ),
    )
    overdue_work_orders = await count_overdue(db, organization_id)
    pending_approvals = await count_pending_approvals(db, organization_id)
    verified_count = await _count(
        db,
        VerifiedKnowledge,
        VerifiedKnowledge.organization_id == organization_id,
    )

    seven_days_ago = dt.datetime.now(dt.UTC) - dt.timedelta(days=7)
    resolved_last_7 = await _count(
        db,
        Incident,
        Incident.organization_id == organization_id,
        Incident.resolved_at.is_not(None),
        Incident.resolved_at >= seven_days_ago,
    )

    # Document indexing status breakdown.
    doc_rows = (
        await db.execute(
            select(Document.status, func.count())
            .where(Document.organization_id == organization_id)
            .group_by(Document.status)
        )
    ).all()
    doc_counts = {status: count for status, count in doc_rows}
    documents = DocumentStatusCounts(
        indexed=int(doc_counts.get(DocumentStatus.indexed, 0)),
        processing=int(doc_counts.get(DocumentStatus.processing, 0)),
        pending=int(doc_counts.get(DocumentStatus.pending, 0)),
        failed=int(doc_counts.get(DocumentStatus.failed, 0)),
    )

    # Incidents by severity (open only).
    sev_rows = (
        await db.execute(
            select(Incident.severity, func.count())
            .where(
                Incident.organization_id == organization_id,
                Incident.status != IncidentStatus.closed,
            )
            .group_by(Incident.severity)
        )
    ).all()
    incidents_by_severity = {s.value: 0 for s in Severity}
    for severity, count in sev_rows:
        incidents_by_severity[severity.value] = int(count)

    wo_rows = (
        await db.execute(
            select(WorkOrder.status, func.count())
            .where(WorkOrder.organization_id == organization_id)
            .group_by(WorkOrder.status)
        )
    ).all()
    work_orders_by_status = {s.value: 0 for s in WorkOrderStatus}
    for status, count in wo_rows:
        work_orders_by_status[status.value] = int(count)

    recent_incidents = (
        await db.execute(
            select(Incident)
            .where(Incident.organization_id == organization_id)
            .order_by(Incident.created_at.desc())
            .limit(5)
        )
    ).scalars().all()

    recent_work_orders = (
        await db.execute(
            select(WorkOrder)
            .where(WorkOrder.organization_id == organization_id)
            .order_by(WorkOrder.updated_at.desc())
            .limit(5)
        )
    ).scalars().all()

    recent_activity = (
        await db.execute(
            select(AuditLog)
            .where(AuditLog.organization_id == organization_id)
            .order_by(AuditLog.created_at.desc())
            .limit(10)
        )
    ).scalars().all()

    metrics = DashboardMetrics(
        open_incidents=open_incidents,
        active_work_orders=active_work_orders,
        overdue_work_orders=overdue_work_orders,
        resolved_last_7_days=resolved_last_7,
        pending_approvals=pending_approvals,
        verified_knowledge_count=verified_count,
        documents=documents,
        incidents_by_severity=incidents_by_severity,
        work_orders_by_status=work_orders_by_status,
    )
    return DashboardOut(
        metrics=metrics,
        recent_incidents=[IncidentOut.model_validate(i) for i in recent_incidents],
        recent_work_orders=[WorkOrderOut.model_validate(w) for w in recent_work_orders],
        recent_activity=[AuditLogOut.model_validate(a) for a in recent_activity],
    )
