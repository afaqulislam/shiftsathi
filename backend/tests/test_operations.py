"""Incident / work-order workflow, verification and dashboard tests."""

from __future__ import annotations

import pytest
from httpx import AsyncClient

from tests.conftest import DEFAULT_PASSWORD, auth_headers, login, register_account

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]


async def _workspace(client: AsyncClient, org: str, slug: str):
    """Register an admin and invite a supervisor + worker."""
    admin = await register_account(
        client, org_name=org, email=f"admin@{slug}.example"
    )
    admin_token = admin["access_token"]
    for role, email in (("supervisor", f"sup@{slug}.example"), ("worker", f"wrk@{slug}.example")):
        resp = await client.post(
            "/api/v1/auth/members",
            headers=auth_headers(admin_token),
            json={
                "full_name": f"{role.title()} User",
                "email": email,
                "password": DEFAULT_PASSWORD,
                "role": role,
            },
        )
        assert resp.status_code == 201, resp.text
    sup_token = await login(client, f"sup@{slug}.example")
    worker_token = await login(client, f"wrk@{slug}.example")
    return admin_token, sup_token, worker_token


async def _create_incident(client: AsyncClient, token: str, **overrides):
    payload = {
        "title": "Hydraulic press pressure drop",
        "description": "Pressure drops during cycle",
        "machine": "Hydraulic Press H2",
        "severity": "high",
    }
    payload.update(overrides)
    resp = await client.post(
        "/api/v1/incidents", headers=auth_headers(token), json=payload
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


# ----------------------------- Incidents ----------------------------------


async def test_worker_can_report_incident(client: AsyncClient):
    _, _, worker_token = await _workspace(client, "Work Co", "work")
    incident = await _create_incident(client, worker_token)
    assert incident["status"] == "open"
    assert incident["severity"] == "high"


async def test_worker_cannot_change_incident_status(client: AsyncClient):
    _, sup_token, worker_token = await _workspace(client, "Status Co", "status")
    incident = await _create_incident(client, worker_token)
    resp = await client.patch(
        f"/api/v1/incidents/{incident['id']}",
        headers=auth_headers(worker_token),
        json={"status": "investigating"},
    )
    assert resp.status_code == 403

    # Supervisor can.
    resp = await client.patch(
        f"/api/v1/incidents/{incident['id']}",
        headers=auth_headers(sup_token),
        json={"status": "investigating"},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "investigating"


async def test_invalid_incident_transition_rejected(client: AsyncClient):
    _, sup_token, worker_token = await _workspace(client, "Transition Co", "trans")
    incident = await _create_incident(client, worker_token)
    # open -> closed is allowed for supervisor; then closed -> resolved is not.
    await client.patch(
        f"/api/v1/incidents/{incident['id']}",
        headers=auth_headers(sup_token),
        json={"status": "closed"},
    )
    resp = await client.patch(
        f"/api/v1/incidents/{incident['id']}",
        headers=auth_headers(sup_token),
        json={"status": "resolved"},
    )
    assert resp.status_code == 422


async def test_incident_list_filters_and_is_org_scoped(client: AsyncClient):
    admin_token, sup_token, worker_token = await _workspace(client, "Filter Co", "filter")
    await _create_incident(client, worker_token)
    await _create_incident(client, worker_token, title="Second issue", severity="low")

    resp = await client.get(
        "/api/v1/incidents?severity=low", headers=auth_headers(sup_token)
    )
    assert resp.status_code == 200
    assert resp.json()["total"] == 1

    # Other org sees none.
    other = await register_account(
        client, org_name="Other Org", email="admin@otherorg.example"
    )
    resp = await client.get(
        "/api/v1/incidents", headers=auth_headers(other["access_token"])
    )
    assert resp.json()["total"] == 0


# ---------------------------- Work orders ---------------------------------


async def test_supervisor_creates_and_assigns_work_order(client: AsyncClient):
    _, sup_token, worker_token = await _workspace(client, "WO Co", "wo")
    incident = await _create_incident(client, worker_token)

    # Workers cannot create work orders.
    resp = await client.post(
        "/api/v1/work-orders",
        headers=auth_headers(worker_token),
        json={"title": "Fix press", "incident_id": incident["id"]},
    )
    assert resp.status_code == 403

    # Members list to find worker id.
    members = await client.get(
        "/api/v1/auth/members", headers=auth_headers(sup_token)
    )
    worker_id = next(
        m["user"]["id"] for m in members.json() if m["role"] == "worker"
    )

    resp = await client.post(
        "/api/v1/work-orders",
        headers=auth_headers(sup_token),
        json={
            "title": "Fix hydraulic press pressure drop",
            "incident_id": incident["id"],
            "assignee_id": worker_id,
            "priority": "high",
        },
    )
    assert resp.status_code == 201, resp.text
    wo = resp.json()
    assert wo["status"] == "assigned"
    assert wo["assignee"]["full_name"] == "Worker User"
    assert wo["incident_id"] == incident["id"]


async def test_work_order_status_flow(client: AsyncClient):
    _, sup_token, worker_token = await _workspace(client, "Flow Co", "flow")
    members = await client.get("/api/v1/auth/members", headers=auth_headers(sup_token))
    worker_id = next(m["user"]["id"] for m in members.json() if m["role"] == "worker")

    wo = (
        await client.post(
            "/api/v1/work-orders",
            headers=auth_headers(sup_token),
            json={"title": "Replace belt", "assignee_id": worker_id},
        )
    ).json()
    wo_id = wo["id"]

    # Worker assigned: open/assigned -> in_progress.
    resp = await client.post(
        f"/api/v1/work-orders/{wo_id}/status",
        headers=auth_headers(worker_token),
        json={"status": "in_progress"},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "in_progress"

    # Resolving requires notes.
    resp = await client.post(
        f"/api/v1/work-orders/{wo_id}/status",
        headers=auth_headers(worker_token),
        json={"status": "resolved"},
    )
    assert resp.status_code == 422

    # With notes it succeeds and syncs the parent incident if present.
    resp = await client.post(
        f"/api/v1/work-orders/{wo_id}/status",
        headers=auth_headers(worker_token),
        json={"status": "resolved", "resolution_notes": "Belt replaced and tensioned."},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "resolved"
    assert body["resolved_at"] is not None

    # Worker may not close; only supervisor/admin.
    resp = await client.post(
        f"/api/v1/work-orders/{wo_id}/status",
        headers=auth_headers(worker_token),
        json={"status": "closed"},
    )
    assert resp.status_code == 403

    resp = await client.post(
        f"/api/v1/work-orders/{wo_id}/status",
        headers=auth_headers(sup_token),
        json={"status": "closed"},
    )
    assert resp.status_code == 200
    assert resp.json()["closed_at"] is not None


async def test_work_order_resolution_revalidates_on_edit(client: AsyncClient):
    _, sup_token, worker_token = await _workspace(client, "Reval Co", "reval")
    wo = (
        await client.post(
            "/api/v1/work-orders",
            headers=auth_headers(sup_token),
            json={"title": "Calibrate sensor"},
        )
    ).json()
    wo_id = wo["id"]
    await client.post(
        f"/api/v1/work-orders/{wo_id}/status",
        headers=auth_headers(sup_token),
        json={"status": "resolved", "resolution_notes": "Calibrated."},
    )
    verified = await client.post(
        f"/api/v1/work-orders/{wo_id}/verify?verified=true",
        headers=auth_headers(sup_token),
    )
    assert verified.status_code == 200
    assert verified.json()["is_verified"] is True

    # Re-opening the work order must clear verification.
    reopened = await client.post(
        f"/api/v1/work-orders/{wo_id}/status",
        headers=auth_headers(sup_token),
        json={"status": "in_progress"},
    )
    assert reopened.json()["is_verified"] is False


# ------------------------ Verified knowledge (Phase 6) ---------------------


async def test_verification_creates_searchable_knowledge(client: AsyncClient):
    _, sup_token, worker_token = await _workspace(client, "Knowledge Co", "know")
    incident = await _create_incident(client, worker_token)
    wo = (
        await client.post(
            "/api/v1/work-orders",
            headers=auth_headers(sup_token),
            json={"title": "Fix press seal", "incident_id": incident["id"]},
        )
    ).json()
    wo_id = wo["id"]
    await client.post(
        f"/api/v1/work-orders/{wo_id}/status",
        headers=auth_headers(sup_token),
        json={
            "status": "resolved",
            "resolution_notes": "Replaced seal kit SK-40 and refilled oil.",
        },
    )

    # Worker cannot verify.
    resp = await client.post(
        f"/api/v1/work-orders/{wo_id}/verify?verified=true",
        headers=auth_headers(worker_token),
    )
    assert resp.status_code == 403

    resp = await client.post(
        f"/api/v1/work-orders/{wo_id}/verify?verified=true",
        headers=auth_headers(sup_token),
    )
    assert resp.status_code == 200
    assert resp.json()["is_verified"] is True

    # It now appears in verified knowledge with an approver.
    listing = await client.get(
        "/api/v1/verified-knowledge", headers=auth_headers(worker_token)
    )
    assert listing.status_code == 200
    items = listing.json()["items"]
    assert len(items) == 1
    assert items[0]["work_order_id"] == wo_id
    assert items[0]["approved_by"] is not None
    assert "seal" in items[0]["title"]


async def test_cannot_verify_unresolved_or_noteless(client: AsyncClient):
    _, sup_token, _ = await _workspace(client, "VerCo", "verco")
    wo = (
        await client.post(
            "/api/v1/work-orders",
            headers=auth_headers(sup_token),
            json={"title": "Nothing yet"},
        )
    ).json()
    # Not resolved yet.
    resp = await client.post(
        f"/api/v1/work-orders/{wo['id']}/verify?verified=true",
        headers=auth_headers(sup_token),
    )
    assert resp.status_code == 422


# ------------------------------- Dashboard --------------------------------


async def test_dashboard_metrics_match_database(client: AsyncClient):
    _, sup_token, worker_token = await _workspace(client, "Dash Co", "dash")
    members = await client.get("/api/v1/auth/members", headers=auth_headers(sup_token))
    worker_id = next(m["user"]["id"] for m in members.json() if m["role"] == "worker")

    incident = await _create_incident(client, worker_token)
    await client.post(
        "/api/v1/work-orders",
        headers=auth_headers(sup_token),
        json={"title": "Open task", "assignee_id": worker_id, "incident_id": incident["id"]},
    )

    resp = await client.get("/api/v1/dashboard", headers=auth_headers(sup_token))
    assert resp.status_code == 200
    metrics = resp.json()["metrics"]
    assert metrics["open_incidents"] == 1
    assert metrics["active_work_orders"] == 1
    assert metrics["pending_approvals"] == 0
    assert metrics["documents"]["indexed"] == 0
    # Real breakdowns, not fabricated values.
    assert metrics["incidents_by_severity"]["high"] == 1
    assert metrics["incidents_by_severity"]["critical"] == 0
