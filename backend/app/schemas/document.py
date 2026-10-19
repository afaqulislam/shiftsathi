"""Document / knowledge-base schemas."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.enums import DocumentStatus


class DocumentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str
    filename: str
    content_type: str
    size_bytes: int
    page_count: int
    status: DocumentStatus
    error_message: str | None
    checksum: str
    uploaded_by: uuid.UUID | None
    created_at: datetime
    indexed_at: datetime | None
    updated_at: datetime


class DocumentChunkOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    chunk_index: int
    page_number: int | None
    content: str
    token_count: int
    has_embedding: bool = False


class DocumentDetailOut(BaseModel):
    document: DocumentOut
    chunk_count: int


class ChunkPage(BaseModel):
    items: list[DocumentChunkOut]
    total: int
    limit: int
    offset: int


class DocumentListOut(BaseModel):
    items: list[DocumentOut]
    total: int
    limit: int
    offset: int
