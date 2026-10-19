"""Dashboard metric schemas."""

from __future__ import annotations

from pydantic import BaseModel

from app.schemas.incident import AuditLogOut, IncidentOut, WorkOrderOut


class DocumentStatusCounts(BaseModel):
    indexed: int = 0
    processing: int = 0
    pending: int = 0
    failed: int = 0


class DashboardMetrics(BaseModel):
    open_incidents: int
    active_work_orders: int
    overdue_work_orders: int
    resolved_last_7_days: int
    pending_approvals: int
    verified_knowledge_count: int
    documents: DocumentStatusCounts
    incidents_by_severity: dict[str, int]
    work_orders_by_status: dict[str, int]


class DashboardOut(BaseModel):
    metrics: DashboardMetrics
    recent_incidents: list[IncidentOut]
    recent_work_orders: list[WorkOrderOut]
    recent_activity: list[AuditLogOut]
