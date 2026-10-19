"""Verified knowledge schemas."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class VerifiedKnowledgeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    work_order_id: uuid.UUID | None
    incident_id: uuid.UUID | None
    title: str
    machine: str | None
    content: str
    approved_by: uuid.UUID | None
    approved_at: datetime
    created_at: datetime


class VerifiedKnowledgeListOut(BaseModel):
    items: list[VerifiedKnowledgeOut]
    total: int
    limit: int
    offset: int
