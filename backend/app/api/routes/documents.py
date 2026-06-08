"""
Documents API routes: upload, status, and text retrieval.

Per CLAUDE.md §8: All endpoints except /auth/* require Bearer JWT token.
Ownership enforcement: users can only access their own documents.
"""

import logging
import os
import tempfile
import uuid
import json

from fastapi import APIRouter, UploadFile, File, HTTPException, BackgroundTasks, Depends, status
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.models.document import Document
from app.schemas.auth import AuthUser
from app.schemas.common import StandardResponse
from app.services.guest_quota import consume_guest_quota, ensure_guest_quota_available
from app.services.storage import get_storage_service, StorageService
from app.services.nlp_client import get_nlp_client, NLPServiceClient
from app.schemas.document import DocumentListItem, DocumentResponse, DocumentStatusResponse, DocumentTextResponse
from sqlalchemy import select
from sqlalchemy.orm import load_only

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/documents", tags=["documents"])

# File upload constraints
MAX_FILE_SIZE = 25 * 1024 * 1024  # 25 MB
ALLOWED_MIME_TYPES = {"application/pdf", "image/png", "image/jpeg", "image/tiff"}

# Columns to load for list queries (exclude heavy BYTEA and text fields)
_LIST_COLUMNS = [
    Document.id,
    Document.filename,
    Document.storage_path,
    Document.status,
    Document.summary,
    Document.risk_score,
    Document.risk_clauses_json,
    Document.created_at,
    Document.updated_at,
    Document.owner_id,
]


@router.post("/upload", response_model=StandardResponse, status_code=status.HTTP_201_CREATED)
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    current_user: AuthUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    storage: StorageService = Depends(get_storage_service),
    nlp_client: NLPServiceClient = Depends(get_nlp_client),
) -> StandardResponse:
    """
    Upload a document (PDF or image).
    Validates file type and size, saves to PostgreSQL bytea, creates DB record.
    Returns document ID and status "pending".

    Requires: Bearer JWT token (CLAUDE.md §8).
    """
    # Validate MIME type
    if file.content_type not in ALLOWED_MIME_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid file type. Allowed: {', '.join(ALLOWED_MIME_TYPES)}",
        )

    # Read file and validate size
    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File too large. Max size: {MAX_FILE_SIZE / 1024 / 1024} MB",
        )

    if current_user.is_guest:
        await ensure_guest_quota_available(db, current_user.id)

    # Create document record
    doc_id = uuid.uuid4()
    try:
        # Save file to temp location first
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            tmp.write(content)
            tmp_path = tmp.name

        # Save to storage service (returns storage_path and file_content for bytea)
        storage_path, file_content = storage.save_file(tmp_path, file.filename, doc_id)

        # Create DB record with file content in bytea column
        document = Document(
            id=doc_id,
            filename=file.filename,
            storage_path=storage_path,
            file_content=file_content,  # Store binary content in PostgreSQL
            status="pending",
            owner_id=current_user.id,
        )
        db.add(document)
        if current_user.is_guest:
            await consume_guest_quota(db, current_user.id)
        await db.commit()
        await db.refresh(document)

        # Schedule OCR processing (background task)
        background_tasks.add_task(process_document_ocr, doc_id, file.filename, nlp_client)

        doc_response = DocumentResponse.model_validate(document)
        return StandardResponse(
            success=True,
            data=doc_response.model_dump(mode="json"),
            message="Document uploaded successfully.",
        )

    except HTTPException:
        raise
    except Exception as exc:
        await db.rollback()
        logger.error("Failed to upload document: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to upload document. Please try again.",
        ) from exc
    finally:
        if 'tmp_path' in locals() and os.path.exists(tmp_path):
            os.remove(tmp_path)

@router.get("", response_model=StandardResponse)
async def list_documents(
    page: int = 1,
    limit: int = 20,
    current_user: AuthUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> StandardResponse:
    """List documents owned by the current user (CLAUDE.md §8)."""
    from sqlalchemy import func

    offset = (page - 1) * limit

    # Count total documents for pagination metadata
    count_stmt = select(func.count()).select_from(Document).where(
        Document.owner_id == current_user.id
    )
    total_count = (await db.execute(count_stmt)).scalar() or 0

    stmt = (
        select(Document)
        .options(load_only(*_LIST_COLUMNS))
        .where(Document.owner_id == current_user.id)
        .order_by(Document.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    result = await db.execute(stmt)
    documents = result.scalars().all()
    items = [DocumentListItem.model_validate(doc).model_dump(mode="json") for doc in documents]
    return StandardResponse(
        success=True,
        data={
            "items": items,
            "total_count": total_count,
            "page": page,
            "limit": limit,
            "has_more": (offset + len(items)) < total_count,
        },
        message=f"{len(items)} document(s) found.",
    )

@router.get("/count", response_model=StandardResponse)
async def get_document_count(
    current_user: AuthUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> StandardResponse:
    """Get total document count for current user (CLAUDE.md §8)."""
    from sqlalchemy import func

    stmt = select(func.count()).select_from(Document).where(
        Document.owner_id == current_user.id
    )
    result = await db.execute(stmt)
    count = result.scalar() or 0
    return StandardResponse(
        success=True,
        data={"count": count},
        message=f"User has {count} document(s).",
    )


@router.get("/search", response_model=StandardResponse)
async def search_documents(
    q: str = "",
    limit: int = 20,
    current_user: AuthUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> StandardResponse:
    """Search documents by filename for current user (CLAUDE.md §8)."""
    if not q.strip():
        return StandardResponse(success=True, data=[], message="Empty query.")

    stmt = (
        select(Document)
        .options(load_only(*_LIST_COLUMNS))
        .where(Document.owner_id == current_user.id)
        .where(Document.filename.ilike(f"%{q}%"))
        .order_by(Document.created_at.desc())
        .limit(limit)
    )
    result = await db.execute(stmt)
    documents = result.scalars().all()
    items = [DocumentListItem.model_validate(doc).model_dump(mode="json") for doc in documents]
    return StandardResponse(
        success=True,
        data=items,
        message=f"{len(items)} document(s) found matching '{q}'.",
    )


@router.get("/{document_id}", response_model=StandardResponse)
async def get_document(
    document_id: uuid.UUID,
    current_user: AuthUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> StandardResponse:
    """Fetch document metadata. Only owner can access (CLAUDE.md §8)."""
    stmt = select(Document).where(Document.id == document_id)
    result = await db.execute(stmt)
    document = result.scalar_one_or_none()

    if not document:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

    if document.owner_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    doc_response = DocumentResponse.model_validate(document)
    return StandardResponse(
        success=True,
        data=doc_response.model_dump(mode="json"),
        message="Document found.",
    )


@router.get("/{document_id}/status", response_model=StandardResponse)
async def get_document_status(
    document_id: uuid.UUID,
    current_user: AuthUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> StandardResponse:
    """Get document processing status. Only owner can access (CLAUDE.md §8)."""
    stmt = select(Document).where(Document.id == document_id)
    result = await db.execute(stmt)
    document = result.scalar_one_or_none()

    if not document:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

    if document.owner_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    return StandardResponse(
        success=True,
        data=DocumentStatusResponse(id=document.id, status=document.status).model_dump(mode="json"),
        message=f"Document status: {document.status}.",
    )


@router.get("/{document_id}/text", response_model=StandardResponse)
async def get_document_text(
    document_id: uuid.UUID,
    current_user: AuthUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> StandardResponse:
    """
    Get extracted text from document. Only owner can access (CLAUDE.md §8).
    Returns 202 Accepted if still processing, 200 with text if done, 400 if failed.
    """
    stmt = select(Document).where(Document.id == document_id)
    result = await db.execute(stmt)
    document = result.scalar_one_or_none()

    if not document:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

    if document.owner_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    if document.status == "pending" or document.status == "processing":
        raise HTTPException(
            status_code=status.HTTP_202_ACCEPTED,
            detail="Document is still being processed",
        )

    if document.status == "failed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Document processing failed",
        )

    # Status == "done"
    text_response = DocumentTextResponse(
        id=document.id,
        extracted_text=document.extracted_text or "",
        status=document.status,
    )
    return StandardResponse(
        success=True,
        data=text_response.model_dump(mode="json"),
        message="Extracted text retrieved.",
    )

@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    document_id: uuid.UUID,
    current_user: AuthUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    storage: StorageService = Depends(get_storage_service),
    nlp_client: NLPServiceClient = Depends(get_nlp_client),
) -> None:
    """Delete document and its NLP collection. Only owner can delete (CLAUDE.md §8)."""
    stmt = select(Document).where(Document.id == document_id)
    result = await db.execute(stmt)
    document = result.scalar_one_or_none()

    if not document:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

    if document.owner_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    storage.delete_file(document.storage_path)
    await nlp_client.delete_document_collection(document_id)

    await db.delete(document)
    await db.commit()

# ---------------------------------------------------------------------------
# File download endpoint (CLAUDE.md §8 — GET /documents/{id}/file)
# ---------------------------------------------------------------------------

_EXT_TO_MIME: dict[str, str] = {
    ".pdf": "application/pdf",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".tiff": "image/tiff",
    ".tif": "image/tiff",
}


@router.get("/{document_id}/file")
async def download_document_file(
    document_id: uuid.UUID,
    current_user: AuthUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Response:
    """
    Download the original file for a document.

    Reads file_content (BYTEA) from PostgreSQL and serves it with the
    correct Content-Type header.  Only the document owner may download.
    """
    stmt = select(Document).where(Document.id == document_id)
    result = await db.execute(stmt)
    document = result.scalar_one_or_none()

    if not document:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

    if document.owner_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    if not document.file_content:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File content not available for this document.",
        )

    ext = os.path.splitext(document.filename)[1].lower()
    media_type = _EXT_TO_MIME.get(ext, "application/octet-stream")

    return Response(
        content=document.file_content,
        media_type=media_type,
        headers={
            "Content-Disposition": f'attachment; filename="{document.filename}"',
        },
    )


# ---------------------------------------------------------------------------
# Background task: OCR + NLP processing with retry (CLAUDE.md §9)
# ---------------------------------------------------------------------------

MAX_NLP_RETRIES = 3
NLP_RETRY_DELAY_SECONDS = 2


async def process_document_ocr(
    document_id: uuid.UUID,
    filename: str,
    nlp_client: NLPServiceClient,
) -> None:
    """
    Background task to process document via NLP pipeline.

    Fetches file_content from PostgreSQL BYTEA, sends to NLP service,
    and updates document status.  Retry policy: max 3 attempts with
    exponential backoff (2s, 4s).  On final failure marks status=failed.
    """
    import asyncio

    from app.db.session import AsyncSessionLocal

    for attempt in range(1, MAX_NLP_RETRIES + 1):
        try:
            # Fetch document from database to get file_content
            async with AsyncSessionLocal() as db:
                stmt = select(Document).where(Document.id == document_id)
                result = await db.execute(stmt)
                document = result.scalar_one_or_none()

                if not document or not document.file_content:
                    logger.error(
                        "Document %s not found or has no file content", document_id,
                    )
                    return

                # Mark as processing on first attempt
                if attempt == 1:
                    document.status = "processing"
                    await db.commit()

                file_content = document.file_content

            # Call NLP service
            logger.info(
                "NLP processing attempt %d/%d for document %s",
                attempt, MAX_NLP_RETRIES, document_id,
            )
            nlp_result = await nlp_client.process_document(
                document_id, file_content, filename,
            )

            # Update document with result
            async with AsyncSessionLocal() as db:
                stmt = select(Document).where(Document.id == document_id)
                result = await db.execute(stmt)
                document = result.scalar_one_or_none()

                if document:
                    if nlp_result and nlp_result.full_text:
                        document.status = "done"
                        document.extracted_text = nlp_result.full_text
                        document.summary = nlp_result.summary
                        document.risk_score = nlp_result.risk_score
                        document.risk_clauses_json = json.dumps(
                            [rc.model_dump() for rc in nlp_result.risk_clauses],
                            ensure_ascii=False,
                        )
                        await db.commit()
                        logger.info(
                            "Document %s processed successfully on attempt %d",
                            document_id, attempt,
                        )
                        return  # Success — exit retry loop
                    else:
                        logger.warning(
                            "NLP returned empty result for document %s (attempt %d/%d)",
                            document_id, attempt, MAX_NLP_RETRIES,
                        )

        except Exception as exc:
            logger.error(
                "NLP processing error for document %s (attempt %d/%d): %s",
                document_id, attempt, MAX_NLP_RETRIES, exc,
            )

        # Retry with backoff (unless this was the last attempt)
        if attempt < MAX_NLP_RETRIES:
            delay = NLP_RETRY_DELAY_SECONDS * attempt
            logger.info("Retrying NLP for document %s in %ds...", document_id, delay)
            await asyncio.sleep(delay)

    # All retries exhausted — mark as failed
    logger.error(
        "All %d NLP attempts failed for document %s. Marking as failed.",
        MAX_NLP_RETRIES, document_id,
    )
    try:
        async with AsyncSessionLocal() as db:
            stmt = select(Document).where(Document.id == document_id)
            result = await db.execute(stmt)
            document = result.scalar_one_or_none()
            if document:
                document.status = "failed"
                await db.commit()
    except Exception as exc:
        logger.error("Failed to mark document %s as failed: %s", document_id, exc)
