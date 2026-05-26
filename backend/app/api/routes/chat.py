"""
Chat API routes (Sprint 4).
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.models.chat_message import ChatMessage
from app.models.document import Document
from app.models.guest_quota import GuestQuota
from app.schemas.auth import AuthUser
from app.schemas.chat import (
    ChatHistoryItem,
    ChatHistoryResponse,
    ChatMessageRequest,
    ChatMessageResponse,
    ChatSourceItem,
)
from app.schemas.common import StandardResponse
from app.services.nlp_client import NLPServiceClient, get_nlp_client

router = APIRouter(prefix="/chat", tags=["chat"])
DEFAULT_GUEST_FREE_ANALYSES = 5


async def _get_or_create_guest_quota(db: AsyncSession, user_id: uuid.UUID) -> GuestQuota:
    stmt = select(GuestQuota).where(GuestQuota.user_id == user_id)
    result = await db.execute(stmt)
    quota = result.scalar_one_or_none()

    if quota is not None:
        return quota

    quota = GuestQuota(user_id=user_id, remaining_quota=DEFAULT_GUEST_FREE_ANALYSES)
    if hasattr(db, "add"):
        db.add(quota)
    if hasattr(db, "commit"):
        await db.commit()
    if hasattr(db, "refresh"):
        await db.refresh(quota)
    return quota


async def _consume_guest_quota(db: AsyncSession, quota: GuestQuota) -> int:
    if quota.remaining_quota <= 0:
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Guest quota exhausted")

    quota.remaining_quota -= 1
    if hasattr(db, "commit"):
        await db.commit()
    if hasattr(db, "refresh"):
        await db.refresh(quota)
    return quota.remaining_quota


@router.post("/{document_id}/message", response_model=StandardResponse)
async def send_chat_message(
    document_id: uuid.UUID,
    payload: ChatMessageRequest,
    current_user: AuthUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    nlp_client: NLPServiceClient = Depends(get_nlp_client),
) -> StandardResponse:
    """
    Ask a question about one document via RAG chatbot.

    Backend responsibilities (Sprint 4):
    - enforce auth
    - enforce document ownership
    - proxy request to NLP /nlp/chat
    """
    stmt = select(Document).where(Document.id == document_id)
    result = await db.execute(stmt)
    document = result.scalar_one_or_none()

    if not document:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

    if document.owner_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    remaining_quota: int | None = None
    guest_quota: GuestQuota | None = None
    if hasattr(db, "execute"):
        guest_quota = await _get_or_create_guest_quota(db, current_user.id)
        if guest_quota.remaining_quota <= 0:
            raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Guest quota exhausted")

    chat_result = await nlp_client.chat_document(
        document_id=document_id,
        query=payload.message,
        history=[item.model_dump() for item in payload.history],
        top_k=payload.top_k,
    )

    if chat_result is None:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="NLP chat service unavailable",
        )

    response_data = ChatMessageResponse(
        document_id=str(document_id),
        question=payload.message,
        answer=chat_result.answer,
        suggestions=chat_result.suggestions,
        context_chunks_used=chat_result.context_chunks_used,
        sources=[ChatSourceItem(text=chunk) for chunk in chat_result.context_chunks],
        disclaimer=chat_result.disclaimer,
        remaining_quota=None,
    )

    if guest_quota is not None:
        remaining_quota = await _consume_guest_quota(db, guest_quota)
        response_data.remaining_quota = remaining_quota

    # Persist chat message to DB (guarded for fake DB used in tests)
    try:
        if hasattr(db, "add") and hasattr(db, "commit"):
            sources_json = json.dumps(chat_result.context_chunks or [])
            chat_msg = ChatMessage(
                user_id=current_user.id,
                document_id=document_id,
                question=payload.message,
                answer=chat_result.answer,
                sources_json=sources_json,
                created_at=datetime.now(timezone.utc),
            )
            db.add(chat_msg)
            await db.commit()
    except Exception:
        # If persistence fails, do not block the user; log in real app.
        if hasattr(db, "rollback"):
            try:
                await db.rollback()
            except Exception:
                pass

    return StandardResponse(
        success=True,
        data=response_data.model_dump(mode="json"),
        message="Chat response generated.",
    )


@router.get("/{document_id}/history", response_model=StandardResponse)
async def get_chat_history(
    document_id: uuid.UUID,
    current_user: AuthUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> StandardResponse:
    """
    Return persisted chat history for one document.
    """
    stmt = select(Document).where(Document.id == document_id)
    result = await db.execute(stmt)
    document = result.scalar_one_or_none()

    if not document:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

    if document.owner_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    history_stmt = (
        select(ChatMessage)
        .where(ChatMessage.document_id == document_id)
        .where(ChatMessage.user_id == current_user.id)
        .order_by(ChatMessage.created_at.asc())
    )
    history_result = await db.execute(history_stmt)
    history_rows = history_result.scalars().all()

    items: list[ChatHistoryItem] = []
    for row in history_rows:
        try:
            raw_sources = json.loads(row.sources_json) if row.sources_json else []
        except json.JSONDecodeError:
            raw_sources = []

        items.append(
            ChatHistoryItem(
                id=str(row.id),
                document_id=str(row.document_id),
                question=row.question or "",
                answer=row.answer or "",
                sources=[ChatSourceItem(text=str(source)) for source in raw_sources],
                created_at=row.created_at.isoformat() if isinstance(row.created_at, datetime) else str(row.created_at),
            )
        )

    response_data = ChatHistoryResponse(document_id=str(document_id), items=items)

    return StandardResponse(
        success=True,
        data=response_data.model_dump(mode="json"),
        message="Chat history loaded.",
    )
