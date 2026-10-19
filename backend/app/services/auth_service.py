"""Authentication and organization onboarding business logic."""

from __future__ import annotations

import re
import uuid

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import (
    AuthError,
    ConflictError,
    NotFoundError,
    ValidationAppError,
)
from app.core.security import (
    create_access_token,
    hash_password,
    verify_password,
)
from app.models.enums import Role
from app.models.org import Membership, Organization, User
from app.schemas.auth import (
    InviteUserRequest,
    LoginRequest,
    MemberOut,
    MeOut,
    OrganizationOut,
    RegisterRequest,
    UserPublic,
)
from app.services.audit import record_audit


def _slugify(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return slug[:100] or "workspace"


async def _unique_slug(db: AsyncSession, base: str) -> str:
    slug = base
    suffix = 1
    while True:
        existing = await db.scalar(
            select(Organization.id).where(Organization.slug == slug)
        )
        if existing is None:
            return slug
        suffix += 1
        slug = f"{base}-{suffix}"


async def register_organization(
    db: AsyncSession, payload: RegisterRequest
) -> tuple[User, Organization, Role]:
    """Create a new organization together with its first admin user."""
    existing = await db.scalar(
        select(User.id).where(func.lower(User.email) == payload.email.lower())
    )
    if existing:
        raise ConflictError("An account with this email already exists.")

    org = Organization(
        name=payload.organization_name.strip(),
        slug=await _unique_slug(db, _slugify(payload.organization_name)),
    )
    db.add(org)
    await db.flush()

    user = User(
        email=payload.email.lower(),
        full_name=payload.full_name.strip(),
        password_hash=hash_password(payload.password),
    )
    db.add(user)
    await db.flush()

    membership = Membership(user_id=user.id, organization_id=org.id, role=Role.admin)
    db.add(membership)
    await db.flush()

    await record_audit(
        db,
        organization_id=org.id,
        actor_id=user.id,
        action="organization.created",
        entity_type="organization",
        entity_id=org.id,
        detail={"name": org.name},
    )
    return user, org, Role.admin


async def authenticate(
    db: AsyncSession, payload: LoginRequest
) -> tuple[User, Organization, Role]:
    user = await db.scalar(
        select(User).where(func.lower(User.email) == payload.email.lower())
    )
    if not user or not verify_password(payload.password, user.password_hash):
        # Same message for unknown user and bad password (no user enumeration).
        raise AuthError("Invalid email or password.")
    if not user.is_active:
        raise AuthError("This account has been deactivated.")

    row = (
        await db.execute(
            select(Membership, Organization)
            .join(Organization, Organization.id == Membership.organization_id)
            .where(Membership.user_id == user.id)
            .order_by(Membership.created_at.asc())
        )
    ).first()
    if row is None:
        raise AuthError("This account is not a member of any workspace.")

    membership, org = row
    return user, org, membership.role


def issue_token(user: User, org: Organization, role: Role) -> str:
    return create_access_token(subject=str(user.id), org_id=str(org.id), role=role.value)


async def build_me(user: User, org: Organization, role: Role) -> MeOut:
    return MeOut(
        user=UserPublic.model_validate(user),
        organization=OrganizationOut.model_validate(org),
        role=role,
    )


async def change_password(
    db: AsyncSession,
    *,
    user: User,
    current_password: str,
    new_password: str,
) -> None:
    if not verify_password(current_password, user.password_hash):
        raise AuthError("Current password is incorrect.")
    if verify_password(new_password, user.password_hash):
        raise ValidationAppError(
            "New password must be different from the current password."
        )
    user.password_hash = hash_password(new_password)
    db.add(user)
    await record_audit(
        db,
        organization_id=(await _first_org_id(db, user.id)),
        actor_id=user.id,
        action="user.password_changed",
        entity_type="user",
        entity_id=user.id,
    )
    await db.flush()


async def _first_org_id(db: AsyncSession, user_id: uuid.UUID) -> uuid.UUID:
    org_id = await db.scalar(
        select(Membership.organization_id)
        .where(Membership.user_id == user_id)
        .order_by(Membership.created_at.asc())
    )
    if org_id is None:
        raise NotFoundError("This account is not a member of any workspace.")
    return org_id


async def invite_user(
    db: AsyncSession,
    *,
    organization_id: uuid.UUID,
    actor_id: uuid.UUID,
    payload: InviteUserRequest,
) -> MemberOut:
    existing = await db.scalar(
        select(User).where(func.lower(User.email) == payload.email.lower())
    )
    if existing:
        # Attach existing identity to this org if not already a member.
        already = await db.scalar(
            select(Membership.id).where(
                Membership.user_id == existing.id,
                Membership.organization_id == organization_id,
            )
        )
        if already:
            raise ConflictError("This user is already a member of the workspace.")
        membership = Membership(
            user_id=existing.id, organization_id=organization_id, role=payload.role
        )
        db.add(membership)
        await record_audit(
            db,
            organization_id=organization_id,
            actor_id=actor_id,
            action="member.added",
            entity_type="user",
            entity_id=existing.id,
            detail={"role": payload.role.value},
        )
        return MemberOut(user=UserPublic.model_validate(existing), role=payload.role)

    try:
        user = User(
            email=payload.email.lower(),
            full_name=payload.full_name.strip(),
            password_hash=hash_password(payload.password),
        )
        db.add(user)
        await db.flush()
        membership = Membership(
            user_id=user.id, organization_id=organization_id, role=payload.role
        )
        db.add(membership)
        await db.flush()
    except IntegrityError as exc:  # pragma: no cover - race condition guard
        raise ConflictError("Could not create user.") from exc

    await record_audit(
        db,
        organization_id=organization_id,
        actor_id=actor_id,
        action="member.invited",
        entity_type="user",
        entity_id=user.id,
        detail={"role": payload.role.value},
    )
    return MemberOut(user=UserPublic.model_validate(user), role=payload.role)


async def list_members(
    db: AsyncSession, organization_id: uuid.UUID
) -> list[MemberOut]:
    rows = (
        await db.execute(
            select(User, Membership)
            .join(Membership, Membership.user_id == User.id)
            .where(Membership.organization_id == organization_id)
            .order_by(Membership.created_at.asc())
        )
    ).all()
    return [
        MemberOut(user=UserPublic.model_validate(user), role=membership.role)
        for user, membership in rows
    ]


async def get_membership_or_404(
    db: AsyncSession, organization_id: uuid.UUID, user_id: uuid.UUID
) -> Membership:
    membership = await db.scalar(
        select(Membership).where(
            Membership.organization_id == organization_id,
            Membership.user_id == user_id,
        )
    )
    if membership is None:
        raise NotFoundError("User is not a member of this workspace.")
    return membership


async def update_member_role(
    db: AsyncSession,
    *,
    organization_id: uuid.UUID,
    actor_id: uuid.UUID,
    target_user_id: uuid.UUID,
    role: Role,
) -> MemberOut:
    membership = await get_membership_or_404(db, organization_id, target_user_id)
    if target_user_id == actor_id and role != Role.admin:
        # Prevent an admin from locking themselves out.
        admin_count = await db.scalar(
            select(func.count())
            .select_from(Membership)
            .where(
                Membership.organization_id == organization_id,
                Membership.role == Role.admin,
            )
        )
        if (admin_count or 0) <= 1:
            raise ConflictError("Cannot remove the last admin from the workspace.")
    membership.role = role
    await db.flush()
    await record_audit(
        db,
        organization_id=organization_id,
        actor_id=actor_id,
        action="member.role_changed",
        entity_type="user",
        entity_id=target_user_id,
        detail={"role": role.value},
    )
    user = await db.get(User, target_user_id)
    return MemberOut(user=UserPublic.model_validate(user), role=role)
