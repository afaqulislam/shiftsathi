"""Activity (audit trail) schemas."""

from __future__ import annotations

from pydantic import BaseModel

from app.schemas.incident import AuditLogOut


class ActivityListOut(BaseModel):
    items: list[AuditLogOut]
    total: int
    limit: int
    offset: int
