"""Tests for password management, the activity feed, and rate limiting."""

from __future__ import annotations

from httpx import AsyncClient

from tests.conftest import DEFAULT_PASSWORD, auth_headers, login, register_account


async def test_change_password_success(client: AsyncClient) -> None:
    reg = await register_account(client, org_name="Pw Org", email="pw@example.com")
    headers = auth_headers(reg["access_token"])

    resp = await client.post(
        "/api/v1/auth/password",
        json={"current_password": DEFAULT_PASSWORD, "new_password": "newpass1234"},
        headers=headers,
    )
    assert resp.status_code == 204, resp.text

    token = await login(client, "pw@example.com", "newpass1234")
    assert token

    stale = await client.post(
        "/api/v1/auth/login",
        json={"email": "pw@example.com", "password": DEFAULT_PASSWORD},
    )
    assert stale.status_code == 401


async def test_change_password_wrong_current(client: AsyncClient) -> None:
    reg = await register_account(client, org_name="Pw Org 2", email="pw2@example.com")
    headers = auth_headers(reg["access_token"])

    resp = await client.post(
        "/api/v1/auth/password",
        json={"current_password": "totallywrong1", "new_password": "newpass1234"},
        headers=headers,
    )
    assert resp.status_code == 401
    assert resp.json()["error"]["code"] == "unauthorized"


async def test_change_password_rejects_reuse(client: AsyncClient) -> None:
    reg = await register_account(client, org_name="Pw Org 3", email="pw3@example.com")
    headers = auth_headers(reg["access_token"])

    resp = await client.post(
        "/api/v1/auth/password",
        json={"current_password": DEFAULT_PASSWORD, "new_password": DEFAULT_PASSWORD},
        headers=headers,
    )
    assert resp.status_code == 422
    assert resp.json()["error"]["code"] == "validation_error"


async def test_change_password_rejects_weak(client: AsyncClient) -> None:
    reg = await register_account(client, org_name="Pw Org 4", email="pw4@example.com")
    headers = auth_headers(reg["access_token"])

    resp = await client.post(
        "/api/v1/auth/password",
        json={"current_password": DEFAULT_PASSWORD, "new_password": "short"},
        headers=headers,
    )
    assert resp.status_code == 422


async def test_activity_feed_and_isolation(client: AsyncClient) -> None:
    alpha = await register_account(client, org_name="Alpha", email="alpha@example.com")
    alpha_headers = auth_headers(alpha["access_token"])

    created = await client.post(
        "/api/v1/incidents",
        json={"title": "Pump failure", "severity": "high"},
        headers=alpha_headers,
    )
    assert created.status_code == 201, created.text

    feed = await client.get("/api/v1/activity", headers=alpha_headers)
    assert feed.status_code == 200
    body = feed.json()
    assert body["total"] >= 2
    actions = {item["action"] for item in body["items"]}
    assert "incident.created" in actions
    assert "organization.created" in actions

    filtered = await client.get(
        "/api/v1/activity?entity_type=incident", headers=alpha_headers
    )
    assert filtered.status_code == 200
    assert all(
        item["entity_type"] == "incident" for item in filtered.json()["items"]
    )

    beta = await register_account(client, org_name="Beta", email="beta@example.com")
    beta_headers = auth_headers(beta["access_token"])
    beta_feed = await client.get("/api/v1/activity", headers=beta_headers)
    beta_actions = {item["action"] for item in beta_feed.json()["items"]}
    assert "incident.created" not in beta_actions
    assert "organization.created" in beta_actions


async def test_activity_pagination(client: AsyncClient, monkeypatch) -> None:
    reg = await register_account(client, org_name="Paged", email="paged@example.com")
    headers = auth_headers(reg["access_token"])

    for i in range(3):
        resp = await client.post(
            "/api/v1/incidents",
            json={"title": f"Issue {i}", "severity": "low"},
            headers=headers,
        )
        assert resp.status_code == 201, resp.text

    first = await client.get("/api/v1/activity?limit=2&offset=0", headers=headers)
    assert first.status_code == 200
    first_body = first.json()
    assert first_body["limit"] == 2
    assert first_body["offset"] == 0
    assert len(first_body["items"]) == 2
    assert first_body["total"] >= 4

    second = await client.get("/api/v1/activity?limit=2&offset=2", headers=headers)
    second_body = second.json()
    assert len(second_body["items"]) == 2
    first_ids = {i["id"] for i in first_body["items"]}
    second_ids = {i["id"] for i in second_body["items"]}
    assert first_ids.isdisjoint(second_ids)


async def test_auth_rate_limit(client: AsyncClient, monkeypatch) -> None:
    from app.core.config import settings
    from app.core.ratelimit import limiter

    monkeypatch.setattr(settings, "RATE_LIMIT_ENABLED", True)
    monkeypatch.setattr(settings, "RATE_LIMIT_AUTH_PER_MINUTE", 2)
    limiter.reset()
    try:
        payload = {"email": "nobody@example.com", "password": "whatever123"}
        first = await client.post("/api/v1/auth/login", json=payload)
        second = await client.post("/api/v1/auth/login", json=payload)
        assert first.status_code == 401
        assert second.status_code == 401

        third = await client.post("/api/v1/auth/login", json=payload)
        assert third.status_code == 429
        assert third.json()["error"]["code"] == "rate_limited"
    finally:
        limiter.reset()
