"""Authentication / authorization dependencies.

Every protected route depends on ``get_current_context`` which resolves the
JWT into a verified ``CurrentContext``. The organization id is taken from the
token and *re-validated* against the database on every request, so a stale or
forged membership cannot grant access. All data-access queries then filter by
``context.organization_id`` to enforce tenant isolation.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AuthError, PermissionDeniedError
from app.core.security import decode_access_token
from app.db.base import get_db
from app.models.enums import Role
from app.models.org import Membership, Organization, User

# auto_error=False so we can return our own structured 401 body.
_bearer = HTTPBearer(auto_error=False)


@dataclass
class CurrentContext:
    user: User
    organization: Organization
    role: Role

    @property
    def organization_id(self) -> uuid.UUID:
        return self.organization.id

    @property
    def user_id(self) -> uuid.UUID:
        return self.user.id


def _unauthorized(message: str = "Not authenticated") -> AuthError:
    return AuthError(message)


async def get_current_context(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
    db: AsyncSession = Depends(get_db),
) -> CurrentContext:
    if credentials is None or not credentials.credentials:
        raise _unauthorized()
    payload = decode_access_token(credentials.credentials)
    if not payload:
        raise _unauthorized("Invalid or expired token")

    try:
        user_id = uuid.UUID(payload["sub"])
        org_id = uuid.UUID(payload["org"])
    except (KeyError, ValueError) as exc:
        raise _unauthorized("Malformed token") from exc

    result = await db.execute(
        select(User, Membership, Organization)
        .join(Membership, Membership.user_id == User.id)
        .join(Organization, Organization.id == Membership.organization_id)
        .where(
            User.id == user_id,
            Membership.organization_id == org_id,
            User.is_active.is_(True),
        )
    )
    row = result.first()
    if row is None:
        # User removed, deactivated, or no longer a member of the requested org.
        raise _unauthorized("Account is not authorized for this workspace")

    user, membership, organization = row
    return CurrentContext(user=user, organization=organization, role=membership.role)


def require_roles(*allowed: Role):
    """Dependency factory enforcing that the caller has one of ``allowed`` roles."""

    allowed_set = set(allowed)

    async def _guard(
        context: CurrentContext = Depends(get_current_context),
    ) -> CurrentContext:
        if context.role not in allowed_set:
            raise PermissionDeniedError(
                "Your role does not permit this action."
            )
        return context

    return _guard


# Convenience dependencies
require_admin = require_roles(Role.admin)
require_supervisor = require_roles(Role.admin, Role.supervisor)
require_any = require_roles(Role.admin, Role.supervisor, Role.worker)
