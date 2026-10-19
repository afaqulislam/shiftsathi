"""Document ingestion tests: validation, extraction, page metadata, isolation."""

from __future__ import annotations

import pytest
from httpx import AsyncClient

from tests.conftest import (
    auth_headers,
    login,
    make_pdf,
    register_account,
)

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]

SAMPLE_MANUAL = [
    "CNC Milling Machine - Daily Startup Procedure\n"
    "1. Check lubrication oil level before powering the machine.\n"
    "2. Close the safety guard before starting the spindle.\n"
    "3. If the spindle overheats, stop the machine and inform the supervisor.",
    "Troubleshooting - Spindle Overheating\n"
    "If the spindle temperature exceeds 70C, stop operation immediately.\n"
    "Do not bypass the thermal protection circuit. Contact maintenance.\n"
    "Record the error code shown on the control panel.",
]


async def _upload(client: AsyncClient, token: str, *, filename: str, data: bytes, title: str):
    return await client.post(
        "/api/v1/documents",
        headers=auth_headers(token),
        files={"file": (filename, data, "application/pdf")},
        data={"title": title},
    )


async def test_upload_and_index_pdf(client: AsyncClient):
    account = await register_account(client, org_name="Ingest Co", email="a@ingest.example")
    token = account["access_token"]
    pdf = make_pdf(SAMPLE_MANUAL)

    resp = await _upload(client, token, filename="manual.pdf", data=pdf, title="CNC Manual")
    assert resp.status_code == 201, resp.text
    doc = resp.json()
    assert doc["status"] == "indexed"
    assert doc["page_count"] == 2

    # Chunks preserved with page metadata.
    chunks = await client.get(
        f"/api/v1/documents/{doc['id']}/chunks", headers=auth_headers(token)
    )
    assert chunks.status_code == 200
    body = chunks.json()
    assert body["total"] > 0
    pages = {c["page_number"] for c in body["items"]}
    assert pages == {1, 2}
    assert all(c["has_embedding"] for c in body["items"])


async def test_reject_non_pdf(client: AsyncClient):
    account = await register_account(client, org_name="Reject Co", email="a@reject.example")
    token = account["access_token"]
    resp = await client.post(
        "/api/v1/documents",
        headers=auth_headers(token),
        files={"file": ("notes.txt", b"just text", "text/plain")},
    )
    assert resp.status_code == 422
    assert resp.json()["error"]["code"] == "validation_error"


async def test_reject_fake_pdf_extension(client: AsyncClient):
    account = await register_account(client, org_name="Fake Co", email="a@fake.example")
    token = account["access_token"]
    # .pdf name but not a real PDF.
    resp = await _upload(
        client, token, filename="fake.pdf", data=b"not really a pdf", title="Fake"
    )
    assert resp.status_code == 422


async def test_duplicate_document_conflict(client: AsyncClient):
    account = await register_account(client, org_name="Dupe Co", email="a@dupe.example")
    token = account["access_token"]
    pdf = make_pdf(SAMPLE_MANUAL)
    first = await _upload(client, token, filename="m.pdf", data=pdf, title="Manual")
    assert first.status_code == 201
    second = await _upload(client, token, filename="m2.pdf", data=pdf, title="Manual copy")
    assert second.status_code == 409


async def test_worker_cannot_upload_document(client: AsyncClient):
    account = await register_account(client, org_name="Perm Co", email="admin@perm.example")
    token = account["access_token"]
    await client.post(
        "/api/v1/auth/members",
        headers=auth_headers(token),
        json={
            "full_name": "Worker",
            "email": "worker@perm.example",
            "password": "worker1234",
            "role": "worker",
        },
    )
    worker_token = await login(client, "worker@perm.example")
    resp = await _upload(
        client, worker_token, filename="x.pdf", data=make_pdf(SAMPLE_MANUAL), title="X"
    )
    assert resp.status_code == 403


async def test_documents_are_org_scoped(client: AsyncClient):
    a = await register_account(client, org_name="Scope A", email="a@scopea.example")
    b = await register_account(client, org_name="Scope B", email="b@scopeb.example")
    pdf = make_pdf(SAMPLE_MANUAL)
    created = await _upload(
        client, a["access_token"], filename="m.pdf", data=pdf, title="Manual"
    )
    doc_id = created.json()["id"]

    listing = await client.get("/api/v1/documents", headers=auth_headers(b["access_token"]))
    assert listing.json()["total"] == 0

    direct = await client.get(
        f"/api/v1/documents/{doc_id}", headers=auth_headers(b["access_token"])
    )
    assert direct.status_code == 404
