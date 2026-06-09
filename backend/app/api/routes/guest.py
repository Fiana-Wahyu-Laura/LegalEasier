"""
Guest quota API routes.

Provides server-authoritative guest quota information so the frontend
can stay in sync (single source of truth principle).

Per CLAUDE.md §8: All endpoints except /auth/* require Bearer JWT token.
"""

import logging
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.models.document import Document
from app.schemas.auth import AuthUser
from app.schemas.common import StandardResponse
from app.services.guest_quota import (
    DEFAULT_GUEST_FREE_ANALYSES,
    get_or_create_guest_quota,
    consume_guest_quota,
    ensure_guest_quota_available,
    refund_guest_quota,
)
from app.services.nlp_client import NLPServiceClient, get_nlp_client

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/guest", tags=["guest"])


@router.get("/quota", response_model=StandardResponse)
async def get_guest_quota(
    current_user: AuthUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> StandardResponse:
    """
    Return the server-authoritative guest quota for the current user.

    Registered users always get {"remaining": null, "total": null, "is_guest": false}.
    Guest users get their actual remaining count from the database.

    The frontend MUST use this as the source of truth for quota display,
    not the local SharedPreferences value (which can be reset by clearing app data).
    """
    if not current_user.is_guest:
        return StandardResponse(
            success=True,
            data={
                "is_guest": False,
                "remaining": None,
                "total": None,
            },
            message="Registered user — no quota limit.",
        )

    quota = await get_or_create_guest_quota(db, current_user.id)
    return StandardResponse(
        success=True,
        data={
            "is_guest": True,
            "remaining": quota.remaining_quota,
            "total": DEFAULT_GUEST_FREE_ANALYSES,
        },
        message=f"Guest quota: {quota.remaining_quota}/{DEFAULT_GUEST_FREE_ANALYSES} remaining.",
    )


@router.delete("/documents", status_code=status.HTTP_204_NO_CONTENT)
async def delete_guest_documents(
    current_user: AuthUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    nlp_client: NLPServiceClient = Depends(get_nlp_client),
) -> None:
    """
    Soft-delete all documents owned by the current guest user.

    Called by the frontend when a guest signs out — documents exist only
    for the duration of the session.  Registered users cannot call this
    (their documents are persistent).
    """
    if not current_user.is_guest:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only guest users can clear session documents.",
        )

    from sqlalchemy import select as sa_select

    # Find all non-deleted documents owned by this guest
    stmt = sa_select(Document).where(
        Document.owner_id == current_user.id,
        Document.deleted_at.is_(None),
    )
    result = await db.execute(stmt)
    docs = result.scalars().all()

    now = datetime.now(timezone.utc)
    deleted_count = 0
    for doc in docs:
        doc.deleted_at = now
        doc.file_content = None  # Free up storage
        deleted_count += 1

        # Clean up NLP collection (best-effort)
        try:
            await nlp_client.delete_document_collection(doc.id)
        except Exception:
            pass

    await db.commit()
    logger.info(
        "Cleaned up %d guest documents for user %s", deleted_count, current_user.id,
    )
