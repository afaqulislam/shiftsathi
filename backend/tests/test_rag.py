"""Evidence-grounded RAG tests: citations, abstention and isolation."""

from __future__ import annotations

import pytest
from httpx import AsyncClient

from tests.conftest import auth_headers, make_pdf, register_account

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]

MANUAL = [
    "CNC Milling Machine - Daily Startup Procedure\n"
    "1. Check lubrication oil level before powering the machine.\n"
    "2. Close the safety guard before starting the spindle.\n"
    "3. If the spindle overheats, stop the machine and inform the supervisor.",
    "Troubleshooting - Spindle Overheating\n"
    "If the spindle temperature exceeds 70C, stop operation immediately.\n"
    "Do not bypass the thermal protection circuit. Contact maintenance.\n"
    "Record the error code shown on the control panel.",
]


async def _setup_with_manual(client: AsyncClient, email: str, org: str):
    account = await register_account(client, org_name=org, email=email)
    token = account["access_token"]
    pdf = make_pdf(MANUAL)
    resp = await client.post(
        "/api/v1/documents",
        headers=auth_headers(token),
        files={"file": ("cnc_manual.pdf", pdf, "application/pdf")},
        data={"title": "CNC Manual"},
    )
    assert resp.status_code == 201, resp.text
    return token, resp.json()


async def test_grounded_answer_with_valid_citations(client: AsyncClient):
    token, doc = await _setup_with_manual(
        client, "a@rag.example", "RAG Co"
    )
    resp = await client.post(
        "/api/v1/chat/ask",
        headers=auth_headers(token),
        json={
            "question": (
                "manual ke mutabiq spindle overheating thermal protection "
                "temperature error code kaise check karein?"
            )
        },
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()

    # Evidence was sufficient, so no abstention and citations are returned.
    assert body["insufficient_evidence"] is False, body
    assert body["answer"]
    assert len(body["citations"]) >= 1

    # Every citation must point at the actual retrieved document / page.
    for citation in body["citations"]:
        assert citation["document_id"] == doc["id"]
        assert citation["document_title"] == "CNC Manual"
        assert citation["page_number"] in (1, 2)
        assert citation["snippet"]
        assert citation["index"] >= 1


async def test_unsupported_question_abstains(client: AsyncClient):
    token, _ = await _setup_with_manual(client, "b@rag.example", "RAG Co 2")
    resp = await client.post(
        "/api/v1/chat/ask",
        headers=auth_headers(token),
        json={"question": "What is the capital city of France and its population?"},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    # No relevant evidence -> assistant must abstain, not invent an answer.
    assert body["insufficient_evidence"] is True
    assert body["citations"] == []
    # The message should direct the user to a supervisor.
    assert "supervisor" in body["answer"].lower()


async def test_conversation_history_is_scoped_to_user(client: AsyncClient):
    token, _ = await _setup_with_manual(client, "c@rag.example", "RAG Co 3")
    ask = await client.post(
        "/api/v1/chat/ask",
        headers=auth_headers(token),
        json={"question": "spindle overheating procedure"},
    )
    conv_id = ask.json()["conversation_id"]

    listing = await client.get("/api/v1/chat/conversations", headers=auth_headers(token))
    assert listing.status_code == 200
    ids = [c["id"] for c in listing.json()["items"]]
    assert conv_id in ids

    detail = await client.get(
        f"/api/v1/chat/conversations/{conv_id}", headers=auth_headers(token)
    )
    assert detail.status_code == 200
    messages = detail.json()["messages"]
    roles = [m["role"] for m in messages]
    assert roles[:2] == ["user", "assistant"]


async def test_conversations_not_visible_to_other_users(client: AsyncClient):
    # Two users in different orgs.
    token_a, _ = await _setup_with_manual(client, "d@raga.example", "Org RAG A")
    token_b, _ = await _setup_with_manual(client, "e@ragb.example", "Org RAG B")

    ask = await client.post(
        "/api/v1/chat/ask",
        headers=auth_headers(token_a),
        json={"question": "spindle overheating"},
    )
    conv_id = ask.json()["conversation_id"]

    # Org B's user cannot fetch org A's conversation.
    detail = await client.get(
        f"/api/v1/chat/conversations/{conv_id}", headers=auth_headers(token_b)
    )
    assert detail.status_code == 404


async def test_retrieval_is_org_scoped(client: AsyncClient):
    token_a, _ = await _setup_with_manual(client, "f@orga.example", "Isolation Org A")
    account_b = await register_account(
        client, org_name="Isolation Org B", email="g@orgb.example"
    )
    token_b = account_b["access_token"]

    # Org B has no documents; asking must abstain even though a similar manual
    # exists in org A.
    resp = await client.post(
        "/api/v1/chat/ask",
        headers=auth_headers(token_b),
        json={"question": "spindle overheating - manual ke mutabiq kya karna chahiye?"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["insufficient_evidence"] is True
    # Ensure no evidence leaked from org A.
    for citation in body["citations"]:
        assert citation["document_id"] is None
    assert body["citations"] == []
