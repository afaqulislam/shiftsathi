"""Knowledge-base document endpoints."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.deps import CurrentContext, get_current_context, require_supervisor
from app.db.base import get_db
from app.models.enums import DocumentStatus
from app.schemas.document import (
    ChunkPage,
    DocumentChunkOut,
    DocumentDetailOut,
    DocumentListOut,
    DocumentOut,
)
from app.services import document_service

router = APIRouter()


@router.get("", response_model=DocumentListOut)
async def list_documents(
    status_filter: DocumentStatus | None = Query(default=None, alias="status"),
    search: str | None = Query(default=None, max_length=200),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    context: CurrentContext = Depends(get_current_context),
    db: AsyncSession = Depends(get_db),
) -> DocumentListOut:
    items, total = await document_service.list_documents(
        db,
        context.organization_id,
        status=status_filter,
        search=search,
        limit=limit,
        offset=offset,
    )
    return DocumentListOut(
        items=[DocumentOut.model_validate(d) for d in items],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.post("", response_model=DocumentOut, status_code=status.HTTP_201_CREATED)
async def upload_document(
    file: UploadFile = File(...),
    title: str | None = Form(default=None),
    context: CurrentContext = Depends(require_supervisor),
    db: AsyncSession = Depends(get_db),
) -> DocumentOut:
    """Upload and index a PDF. Restricted to supervisors/admins."""
    data = await file.read(settings.MAX_UPLOAD_BYTES + 1)
    document = await document_service.ingest_document(
        db,
        organization_id=context.organization_id,
        uploader_id=context.user_id,
        filename=file.filename or "document.pdf",
        title=title or (file.filename or "document.pdf"),
        content_type=file.content_type or "application/pdf",
        data=data,
    )
    await db.commit()
    return DocumentOut.model_validate(document)


@router.get("/{document_id}", response_model=DocumentDetailOut)
async def get_document(
    document_id: uuid.UUID,
    context: CurrentContext = Depends(get_current_context),
    db: AsyncSession = Depends(get_db),
) -> DocumentDetailOut:
    document = await document_service.get_document(
        db, context.organization_id, document_id
    )
    _, chunk_count = await document_service.list_chunks(
        db, context.organization_id, document_id, limit=1, offset=0
    )
    return DocumentDetailOut(
        document=DocumentOut.model_validate(document), chunk_count=chunk_count
    )


@router.get("/{document_id}/chunks", response_model=ChunkPage)
async def get_document_chunks(
    document_id: uuid.UUID,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    context: CurrentContext = Depends(get_current_context),
    db: AsyncSession = Depends(get_db),
) -> ChunkPage:
    chunks, total = await document_service.list_chunks(
        db, context.organization_id, document_id, limit=limit, offset=offset
    )
    items = [
        DocumentChunkOut(
            id=c.id,
            chunk_index=c.chunk_index,
            page_number=c.page_number,
            content=c.content,
            token_count=c.token_count,
            has_embedding=c.embedding is not None,
        )
        for c in chunks
    ]
    return ChunkPage(items=items, total=total, limit=limit, offset=offset)


@router.post("/{document_id}/reindex", response_model=DocumentOut)
async def reindex_document(
    document_id: uuid.UUID,
    file: UploadFile = File(...),
    context: CurrentContext = Depends(require_supervisor),
    db: AsyncSession = Depends(get_db),
) -> DocumentOut:
    """Re-index only if the uploaded content differs from the stored checksum."""
    document = await document_service.get_document(
        db, context.organization_id, document_id
    )
    data = await file.read(settings.MAX_UPLOAD_BYTES + 1)
    document = await document_service.reindex_document(
        db,
        organization_id=context.organization_id,
        document=document,
        data=data,
    )
    await db.commit()
    return DocumentOut.model_validate(document)


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    document_id: uuid.UUID,
    context: CurrentContext = Depends(require_supervisor),
    db: AsyncSession = Depends(get_db),
) -> None:
    await document_service.delete_document(
        db, context.organization_id, document_id
    )
    await db.commit()
