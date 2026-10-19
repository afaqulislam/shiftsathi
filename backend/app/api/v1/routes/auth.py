"""Authentication, onboarding and workspace-member management."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.deps import CurrentContext, get_current_context, require_admin
from app.core.ratelimit import rate_limit
from app.db.base import get_db
from app.schemas.auth import (
    ChangePasswordRequest,
    InviteUserRequest,
    LoginRequest,
    MemberOut,
    MeOut,
    RegisterRequest,
    TokenResponse,
)
from app.services import auth_service

router = APIRouter()


@router.post(
    "/register",
    response_model=TokenResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(rate_limit("auth"))],
)
async def register(
    payload: RegisterRequest, db: AsyncSession = Depends(get_db)
) -> TokenResponse:
    """Create an organization and its first admin account, then log in."""
    user, org, role = await auth_service.register_organization(db, payload)
    await db.commit()
    token = auth_service.issue_token(user, org, role)
    return TokenResponse(
        access_token=token, expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
    )


@router.post(
    "/login",
    response_model=TokenResponse,
    dependencies=[Depends(rate_limit("auth"))],
)
async def login(
    payload: LoginRequest, db: AsyncSession = Depends(get_db)
) -> TokenResponse:
    user, org, role = await auth_service.authenticate(db, payload)
    await db.commit()
    token = auth_service.issue_token(user, org, role)
    return TokenResponse(
        access_token=token, expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
    )


@router.get("/me", response_model=MeOut)
async def me(context: CurrentContext = Depends(get_current_context)) -> MeOut:
    return await auth_service.build_me(
        context.user, context.organization, context.role
    )


@router.post(
    "/password",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(rate_limit("auth"))],
)
async def change_password(
    payload: ChangePasswordRequest,
    context: CurrentContext = Depends(get_current_context),
    db: AsyncSession = Depends(get_db),
) -> None:
    await auth_service.change_password(
        db,
        user=context.user,
        current_password=payload.current_password,
        new_password=payload.new_password,
    )
    await db.commit()


@router.get("/members", response_model=list[MemberOut])
async def list_members(
    context: CurrentContext = Depends(get_current_context),
    db: AsyncSession = Depends(get_db),
) -> list[MemberOut]:
    return await auth_service.list_members(db, context.organization_id)


@router.post(
    "/members",
    response_model=MemberOut,
    status_code=status.HTTP_201_CREATED,
)
async def invite_member(
    payload: InviteUserRequest,
    context: CurrentContext = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> MemberOut:
    member = await auth_service.invite_user(
        db,
        organization_id=context.organization_id,
        actor_id=context.user_id,
        payload=payload,
    )
    await db.commit()
    return member


@router.patch("/members/{user_id}/role", response_model=MemberOut)
async def change_role(
    user_id: uuid.UUID,
    role: str,
    context: CurrentContext = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> MemberOut:
    from app.core.errors import ValidationAppError
    from app.models.enums import Role

    try:
        parsed = Role(role)
    except ValueError as exc:
        raise ValidationAppError("Invalid role.") from exc
    member = await auth_service.update_member_role(
        db,
        organization_id=context.organization_id,
        actor_id=context.user_id,
        target_user_id=user_id,
        role=parsed,
    )
    await db.commit()
    return member
