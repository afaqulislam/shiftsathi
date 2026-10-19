"""Authentication, role enforcement, and cross-organization isolation tests."""

from __future__ import annotations

import pytest
from httpx import AsyncClient

from tests.conftest import auth_headers, login, register_account

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]


async def test_register_creates_org_and_admin(client: AsyncClient):
    data = await register_account(
        client, org_name="Karachi Textiles", email="admin@kt.example"
    )
    assert data["access_token"]
    me = await client.get(
        "/api/v1/auth/me", headers=auth_headers(data["access_token"])
    )
    assert me.status_code == 200
    body = me.json()
    assert body["organization"]["name"] == "Karachi Textiles"
    assert body["role"] == "admin"


async def test_login_rejects_bad_password(client: AsyncClient):
    await register_account(client, org_name="Lahore Motors", email="admin@lm.example")
    resp = await client.post(
        "/api/v1/auth/login",
        json={"email": "admin@lm.example", "password": "wrongpass1"},
    )
    assert resp.status_code == 401
    assert resp.json()["error"]["code"] == "unauthorized"


async def test_unauthenticated_request_is_rejected(client: AsyncClient):
    resp = await client.get("/api/v1/incidents")
    assert resp.status_code == 401


async def test_invalid_token_is_rejected(client: AsyncClient):
    resp = await client.get(
        "/api/v1/incidents", headers={"Authorization": "Bearer not-a-real-token"}
    )
    assert resp.status_code == 401


async def test_worker_cannot_manage_members(client: AsyncClient):
    admin = await register_account(
        client, org_name="Faisalabad Mills", email="admin@fm.example"
    )
    token = admin["access_token"]
    # Admin invites a worker.
    resp = await client.post(
        "/api/v1/auth/members",
        headers=auth_headers(token),
        json={
            "full_name": "Worker One",
            "email": "worker1@fm.example",
            "password": "worker1234",
            "role": "worker",
        },
    )
    assert resp.status_code == 201, resp.text

    worker_token = await login(client, "worker1@fm.example")
    # Worker may not invite others.
    resp = await client.post(
        "/api/v1/auth/members",
        headers=auth_headers(worker_token),
        json={
            "full_name": "Other",
            "email": "other@fm.example",
            "password": "worker1234",
            "role": "worker",
        },
    )
    assert resp.status_code == 403


async def test_cross_organization_isolation(client: AsyncClient):
    # Two separate organizations.
    org_a = await register_account(
        client, org_name="Org A", email="admin@orga.example"
    )
    org_b = await register_account(
        client, org_name="Org B", email="admin@orgb.example"
    )
    token_a = org_a["access_token"]
    token_b = org_b["access_token"]

    # Org A creates an incident.
    created = await client.post(
        "/api/v1/incidents",
        headers=auth_headers(token_a),
        json={"title": "Press machine jam", "description": "Jam near feeder", "severity": "high"},
    )
    assert created.status_code == 201, created.text
    incident_id = created.json()["id"]

    # Org B cannot see it in a list...
    listing = await client.get("/api/v1/incidents", headers=auth_headers(token_b))
    assert listing.status_code == 200
    assert listing.json()["total"] == 0

    # ...and cannot fetch it directly (404, not a leak).
    direct = await client.get(
        f"/api/v1/incidents/{incident_id}", headers=auth_headers(token_b)
    )
    assert direct.status_code == 404
