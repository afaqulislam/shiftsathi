"""Work-order endpoints."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import CurrentContext, require_any, require_supervisor
from app.db.base import get_db
from app.models.enums import Priority, WorkOrderStatus
from app.schemas.incident import (
    WorkOrderCreate,
    WorkOrderListOut,
    WorkOrderOut,
    WorkOrderStatusUpdate,
    WorkOrderUpdate,
)
from app.services import work_order_service

router = APIRouter()


@router.get("", response_model=WorkOrderListOut)
async def list_work_orders(
    status_filter: WorkOrderStatus | None = Query(default=None, alias="status"),
    priority: Priority | None = Query(default=None),
    assignee_id: uuid.UUID | None = Query(default=None),
    incident_id: uuid.UUID | None = Query(default=None),
    machine: str | None = Query(default=None, max_length=200),
    search: str | None = Query(default=None, max_length=200),
    overdue_only: bool = Query(default=False),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    context: CurrentContext = Depends(require_any),
    db: AsyncSession = Depends(get_db),
) -> WorkOrderListOut:
    items, total = await work_order_service.list_work_orders(
        db,
        context.organization_id,
        status=status_filter,
        priority=priority,
        assignee_id=assignee_id,
        incident_id=incident_id,
        machine=machine,
        search=search,
        overdue_only=overdue_only,
        limit=limit,
        offset=offset,
    )
    return WorkOrderListOut(
        items=[WorkOrderOut.model_validate(w) for w in items],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.post("", response_model=WorkOrderOut, status_code=status.HTTP_201_CREATED)
async def create_work_order(
    payload: WorkOrderCreate,
    context: CurrentContext = Depends(require_supervisor),
    db: AsyncSession = Depends(get_db),
) -> WorkOrderOut:
    work_order = await work_order_service.create_work_order(
        db,
        organization_id=context.organization_id,
        actor_id=context.user_id,
        payload=payload,
    )
    await db.commit()
    return WorkOrderOut.model_validate(work_order)


@router.get("/{work_order_id}", response_model=WorkOrderOut)
async def get_work_order(
    work_order_id: uuid.UUID,
    context: CurrentContext = Depends(require_any),
    db: AsyncSession = Depends(get_db),
) -> WorkOrderOut:
    work_order = await work_order_service.get_work_order(
        db, context.organization_id, work_order_id
    )
    return WorkOrderOut.model_validate(work_order)


@router.patch("/{work_order_id}", response_model=WorkOrderOut)
async def update_work_order(
    work_order_id: uuid.UUID,
    payload: WorkOrderUpdate,
    context: CurrentContext = Depends(require_any),
    db: AsyncSession = Depends(get_db),
) -> WorkOrderOut:
    work_order = await work_order_service.get_work_order(
        db, context.organization_id, work_order_id
    )
    work_order = await work_order_service.update_work_order(
        db,
        organization_id=context.organization_id,
        actor_id=context.user_id,
        role=context.role,
        work_order=work_order,
        payload=payload,
    )
    await db.commit()
    return WorkOrderOut.model_validate(work_order)


@router.post("/{work_order_id}/status", response_model=WorkOrderOut)
async def change_status(
    work_order_id: uuid.UUID,
    payload: WorkOrderStatusUpdate,
    context: CurrentContext = Depends(require_any),
    db: AsyncSession = Depends(get_db),
) -> WorkOrderOut:
    work_order = await work_order_service.get_work_order(
        db, context.organization_id, work_order_id
    )
    work_order = await work_order_service.change_status(
        db,
        organization_id=context.organization_id,
        actor_id=context.user_id,
        role=context.role,
        work_order=work_order,
        new_status=payload.status,
        resolution_notes=payload.resolution_notes,
    )
    await db.commit()
    return WorkOrderOut.model_validate(work_order)


@router.post("/{work_order_id}/verify", response_model=WorkOrderOut)
async def verify_work_order(
    work_order_id: uuid.UUID,
    verified: bool = Query(default=True),
    context: CurrentContext = Depends(require_supervisor),
    db: AsyncSession = Depends(get_db),
) -> WorkOrderOut:
    work_order = await work_order_service.get_work_order(
        db, context.organization_id, work_order_id
    )
    work_order, _ = await work_order_service.verify_work_order(
        db,
        organization_id=context.organization_id,
        actor_id=context.user_id,
        actor_role=context.role,
        work_order=work_order,
        verified=verified,
    )
    await db.commit()
    return WorkOrderOut.model_validate(work_order)
