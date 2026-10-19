"""Document ingestion: validation, extraction, chunking, embedding, storage."""

from __future__ import annotations

import hashlib
import io
import logging
import uuid
from dataclasses import dataclass

from pypdf import PdfReader
from pypdf.errors import PdfReadError
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.errors import ConflictError, NotFoundError, ValidationAppError
from app.db.base import utcnow
from app.models.document import Document, DocumentChunk
from app.models.enums import DocumentStatus
from app.services.ai.provider import AIProvider, get_ai_provider

logger = logging.getLogger("shiftsathi.documents")

PDF_MAGIC = b"%PDF"


@dataclass
class ExtractedPage:
    page_number: int
    text: str


@dataclass
class Chunk:
    page_number: int | None
    text: str


def compute_checksum(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def validate_pdf(data: bytes, filename: str) -> None:
    if not filename.lower().endswith(".pdf"):
        raise ValidationAppError("Only PDF files are supported.")
    if len(data) == 0:
        raise ValidationAppError("The uploaded file is empty.")
    if len(data) > settings.MAX_UPLOAD_BYTES:
        limit_mb = settings.MAX_UPLOAD_BYTES // (1024 * 1024)
        raise ValidationAppError(f"File exceeds the {limit_mb} MB limit.")
    if not data.startswith(PDF_MAGIC):
        raise ValidationAppError("File is not a valid PDF.")


def extract_text(data: bytes) -> list[ExtractedPage]:
    """Extract per-page text from a PDF.

    Raises ValidationAppError for encrypted / corrupted PDFs. Page numbers are
    1-indexed to match how humans refer to documents.
    """
    try:
        reader = PdfReader(io.BytesIO(data))
        if reader.is_encrypted:
            try:
                if reader.decrypt("") == 0:  # type: ignore[arg-type]
                    raise ValidationAppError("Encrypted PDFs are not supported.")
            except Exception as exc:  # noqa: BLE001
                raise ValidationAppError("Encrypted PDFs are not supported.") from exc
        if len(reader.pages) > settings.MAX_PDF_PAGES:
            raise ValidationAppError(
                f"PDF has too many pages (max {settings.MAX_PDF_PAGES})."
            )
        pages: list[ExtractedPage] = []
        for i, page in enumerate(reader.pages, start=1):
            try:
                text = page.extract_text() or ""
            except Exception:  # noqa: BLE001 - one bad page shouldn't fail the doc
                logger.warning("Failed to extract page %s", i)
                text = ""
            pages.append(ExtractedPage(page_number=i, text=_normalise(text)))
        return pages
    except ValidationAppError:
        raise
    except (PdfReadError, ValueError, OSError) as exc:
        raise ValidationAppError("Could not read PDF content.") from exc


def _normalise(text: str) -> str:
    # Collapse excessive whitespace while preserving paragraph breaks.
    lines = [ln.strip() for ln in text.replace("\x00", " ").splitlines()]
    kept = [ln for ln in lines if ln]
    return "\n".join(kept)


def chunk_pages(pages: list[ExtractedPage]) -> list[Chunk]:
    """Split page text into overlapping character chunks.

    Chunks never span pages, so each chunk keeps a single accurate page number.
    """
    chunks: list[Chunk] = []
    size = settings.CHUNK_SIZE
    overlap = settings.CHUNK_OVERLAP
    for page in pages:
        text = page.text.strip()
        if not text:
            continue
        start = 0
        while start < len(text):
            end = min(start + size, len(text))
            piece = text[start:end].strip()
            if piece:
                chunks.append(Chunk(page_number=page.page_number, text=piece))
            if end >= len(text):
                break
            start = max(end - overlap, start + 1)
    return chunks


def _approx_tokens(text: str) -> int:
    return max(1, len(text) // 4)


async def find_duplicate(
    db: AsyncSession, organization_id: uuid.UUID, checksum: str
) -> Document | None:
    return await db.scalar(
        select(Document).where(
            Document.organization_id == organization_id,
            Document.checksum == checksum,
        )
    )


async def ingest_document(
    db: AsyncSession,
    *,
    organization_id: uuid.UUID,
    uploader_id: uuid.UUID,
    filename: str,
    title: str,
    content_type: str,
    data: bytes,
    provider: AIProvider | None = None,
) -> Document:
    """Full ingestion pipeline. Marks the document failed on any error."""
    validate_pdf(data, filename)
    checksum = compute_checksum(data)

    duplicate = await find_duplicate(db, organization_id, checksum)
    if duplicate is not None:
        raise ConflictError(
            f"This document is already in the knowledge base as '{duplicate.title}'."
        )

    document = Document(
        organization_id=organization_id,
        title=title.strip() or filename,
        filename=filename,
        content_type=content_type or "application/pdf",
        size_bytes=len(data),
        checksum=checksum,
        status=DocumentStatus.processing,
        uploaded_by=uploader_id,
    )
    db.add(document)
    await db.flush()

    try:
        pages = extract_text(data)
        document.page_count = len(pages)
        chunks = chunk_pages(pages)
        if not chunks:
            raise ValidationAppError(
                "No extractable text found. The PDF may be a scanned image."
            )

        provider = provider or get_ai_provider()
        vectors = await provider.embed([c.text for c in chunks])

        for idx, (chunk, vector) in enumerate(zip(chunks, vectors, strict=True)):
            db.add(
                DocumentChunk(
                    organization_id=organization_id,
                    document_id=document.id,
                    chunk_index=idx,
                    page_number=chunk.page_number,
                    content=chunk.text,
                    token_count=_approx_tokens(chunk.text),
                    embedding=vector,
                )
            )
        document.status = DocumentStatus.indexed
        document.error_message = None
        document.indexed_at = utcnow()
        await db.flush()
    except Exception as exc:  # noqa: BLE001
        document.status = DocumentStatus.failed
        document.error_message = str(exc)[:1000]
        await db.flush()
        logger.error("Ingestion failed for document %s: %s", document.id, type(exc).__name__)
        if isinstance(exc, (ValidationAppError, ConflictError)):
            raise
        # Unexpected (e.g. provider) error: surface a clean message.
        raise ValidationAppError(
            "Document indexing failed. It may require an AI provider to be configured."
        ) from exc

    return document


async def reindex_document(
    db: AsyncSession,
    *,
    organization_id: uuid.UUID,
    document: Document,
    data: bytes,
    provider: AIProvider | None = None,
) -> Document:
    """Re-index a document whose content changed (checksum differs)."""
    validate_pdf(data, document.filename)
    new_checksum = compute_checksum(data)
    if new_checksum == document.checksum:
        # Content unchanged - skip work, keep existing embeddings.
        return document

    document.checksum = new_checksum
    document.status = DocumentStatus.processing
    document.size_bytes = len(data)
    await db.execute(
        delete(DocumentChunk).where(DocumentChunk.document_id == document.id)
    )
    await db.flush()

    try:
        pages = extract_text(data)
        document.page_count = len(pages)
        chunks = chunk_pages(pages)
        if not chunks:
            raise ValidationAppError("No extractable text found.")
        provider = provider or get_ai_provider()
        vectors = await provider.embed([c.text for c in chunks])
        for idx, (chunk, vector) in enumerate(zip(chunks, vectors, strict=True)):
            db.add(
                DocumentChunk(
                    organization_id=organization_id,
                    document_id=document.id,
                    chunk_index=idx,
                    page_number=chunk.page_number,
                    content=chunk.text,
                    token_count=_approx_tokens(chunk.text),
                    embedding=vector,
                )
            )
        document.status = DocumentStatus.indexed
        document.error_message = None
        document.indexed_at = utcnow()
        await db.flush()
    except Exception as exc:  # noqa: BLE001
        document.status = DocumentStatus.failed
        document.error_message = str(exc)[:1000]
        await db.flush()
        if isinstance(exc, ValidationAppError):
            raise
        raise ValidationAppError("Re-indexing failed.") from exc
    return document


async def get_document(
    db: AsyncSession, organization_id: uuid.UUID, document_id: uuid.UUID
) -> Document:
    doc = await db.scalar(
        select(Document).where(
            Document.id == document_id,
            Document.organization_id == organization_id,
        )
    )
    if doc is None:
        raise NotFoundError("Document not found.")
    return doc


async def list_documents(
    db: AsyncSession,
    organization_id: uuid.UUID,
    *,
    status: DocumentStatus | None = None,
    search: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[Document], int]:
    conditions = [Document.organization_id == organization_id]
    if status is not None:
        conditions.append(Document.status == status)
    if search:
        conditions.append(Document.title.ilike(f"%{search}%"))

    total = await db.scalar(
        select(func.count()).select_from(Document).where(*conditions)
    )
    rows = (
        await db.execute(
            select(Document)
            .where(*conditions)
            .order_by(Document.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
    ).scalars().all()
    return list(rows), int(total or 0)


async def list_chunks(
    db: AsyncSession,
    organization_id: uuid.UUID,
    document_id: uuid.UUID,
    *,
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[DocumentChunk], int]:
    await get_document(db, organization_id, document_id)
    total = await db.scalar(
        select(func.count())
        .select_from(DocumentChunk)
        .where(DocumentChunk.document_id == document_id)
    )
    rows = (
        await db.execute(
            select(DocumentChunk)
            .where(
                DocumentChunk.document_id == document_id,
                DocumentChunk.organization_id == organization_id,
            )
            .order_by(DocumentChunk.chunk_index.asc())
            .limit(limit)
            .offset(offset)
        )
    ).scalars().all()
    return list(rows), int(total or 0)


async def delete_document(
    db: AsyncSession, organization_id: uuid.UUID, document_id: uuid.UUID
) -> None:
    doc = await get_document(db, organization_id, document_id)
    await db.delete(doc)
    await db.flush()
