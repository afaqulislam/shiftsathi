"""AI assistant (RAG) endpoints."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import CurrentContext, require_any
from app.core.ratelimit import rate_limit
from app.db.base import get_db
from app.schemas.chat import (
    AskRequest,
    AskResponse,
    ConversationDetailOut,
    ConversationListOut,
    ConversationOut,
    MessageOut,
)
from app.services import rag_service

router = APIRouter()


@router.post(
    "/ask",
    response_model=AskResponse,
    dependencies=[Depends(rate_limit("ai"))],
)
async def ask(
    payload: AskRequest,
    context: CurrentContext = Depends(require_any),
    db: AsyncSession = Depends(get_db),
) -> AskResponse:
    result = await rag_service.answer_question(
        db,
        organization_id=context.organization_id,
        user_id=context.user_id,
        question=payload.question,
        conversation_id=payload.conversation_id,
    )
    await db.commit()
    return result


@router.get("/conversations", response_model=ConversationListOut)
async def list_conversations(
    context: CurrentContext = Depends(require_any),
    db: AsyncSession = Depends(get_db),
) -> ConversationListOut:
    items = await rag_service.list_conversations(
        db, context.organization_id, context.user_id
    )
    return ConversationListOut(
        items=[ConversationOut.model_validate(c) for c in items]
    )


@router.get("/conversations/{conversation_id}", response_model=ConversationDetailOut)
async def get_conversation(
    conversation_id: uuid.UUID,
    context: CurrentContext = Depends(require_any),
    db: AsyncSession = Depends(get_db),
) -> ConversationDetailOut:
    conversation = await rag_service.get_conversation(
        db, context.organization_id, context.user_id, conversation_id
    )
    return ConversationDetailOut(
        conversation=ConversationOut.model_validate(conversation),
        messages=[MessageOut.model_validate(m) for m in conversation.messages],
    )


@router.delete(
    "/conversations/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT
)
async def delete_conversation(
    conversation_id: uuid.UUID,
    context: CurrentContext = Depends(require_any),
    db: AsyncSession = Depends(get_db),
) -> None:
    await rag_service.delete_conversation(
        db, context.organization_id, context.user_id, conversation_id
    )
    await db.commit()
