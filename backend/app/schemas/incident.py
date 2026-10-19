"""Incident and work-order schemas."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import IncidentStatus, Priority, Severity, WorkOrderStatus

# ----------------------------------------------------------------------------
# Incidents
# ----------------------------------------------------------------------------


class IncidentCreate(BaseModel):
    title: str = Field(min_length=3, max_length=300)
    description: str = Field(default="", max_length=5000)
    machine: str | None = Field(default=None, max_length=200)
    severity: Severity = Severity.medium


class IncidentUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=3, max_length=300)
    description: str | None = Field(default=None, max_length=5000)
    machine: str | None = Field(default=None, max_length=200)
    severity: Severity | None = None
    status: IncidentStatus | None = None
    resolution_notes: str | None = Field(default=None, max_length=5000)


class IncidentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str
    description: str
    machine: str | None
    severity: Severity
    status: IncidentStatus
    reported_by: uuid.UUID | None
    resolution_notes: str | None
    created_at: datetime
    updated_at: datetime
    resolved_at: datetime | None


class IncidentListOut(BaseModel):
    items: list[IncidentOut]
    total: int
    limit: int
    offset: int


# ----------------------------------------------------------------------------
# Work orders
# ----------------------------------------------------------------------------


class WorkOrderCreate(BaseModel):
    title: str | None = Field(default=None, max_length=300)
    description: str = Field(default="", max_length=5000)
    machine: str | None = Field(default=None, max_length=200)
    priority: Priority = Priority.medium
    incident_id: uuid.UUID | None = None
    assignee_id: uuid.UUID | None = None
    due_date: datetime | None = None


class WorkOrderUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=3, max_length=300)
    description: str | None = Field(default=None, max_length=5000)
    machine: str | None = Field(default=None, max_length=200)
    priority: Priority | None = None
    assignee_id: uuid.UUID | None = None
    due_date: datetime | None = None
    resolution_notes: str | None = Field(default=None, max_length=5000)


class WorkOrderStatusUpdate(BaseModel):
    status: WorkOrderStatus
    resolution_notes: str | None = Field(default=None, max_length=5000)


class AssigneeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    full_name: str
    email: str


class WorkOrderOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    incident_id: uuid.UUID | None
    title: str
    description: str
    machine: str | None
    priority: Priority
    status: WorkOrderStatus
    assignee_id: uuid.UUID | None
    assignee: AssigneeOut | None = None
    created_by: uuid.UUID | None
    due_date: datetime | None
    resolution_notes: str | None
    is_verified: bool
    verified_by: uuid.UUID | None
    verified_at: datetime | None
    created_at: datetime
    updated_at: datetime
    resolved_at: datetime | None
    closed_at: datetime | None


class WorkOrderListOut(BaseModel):
    items: list[WorkOrderOut]
    total: int
    limit: int
    offset: int


class VerifyWorkOrderRequest(BaseModel):
    verified: bool = True
    note: str | None = Field(default=None, max_length=2000)


class AuditLogOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    actor_id: uuid.UUID | None
    action: str
    entity_type: str
    entity_id: uuid.UUID | None
    detail: dict | None
    created_at: datetime
