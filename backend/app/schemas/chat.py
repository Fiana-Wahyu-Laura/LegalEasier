"""
Schemas for chat API (Sprint 4).
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class ChatMessageHistoryItem(BaseModel):
    """Conversation history item sent by frontend."""

    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=4000)

    model_config = ConfigDict(extra="forbid")


class ChatMessageRequest(BaseModel):
    """Request body for POST /chat/{document_id}/message."""

    message: str = Field(min_length=1, max_length=4000, description="User question.")
    history: list[ChatMessageHistoryItem] = Field(
        default_factory=list,
        max_length=20,
        description="Optional latest conversation history.",
    )
    top_k: int = Field(default=5, ge=1, le=10, description="Number of context chunks.")

    model_config = ConfigDict(extra="forbid")


class ChatSourceItem(BaseModel):
    """Minimal source/context info returned to frontend."""

    text: str


class ChatMessageResponse(BaseModel):
    """Response payload for chat endpoint."""

    document_id: str
    question: str
    answer: str
    suggestions: list[str] = Field(default_factory=list)
    context_chunks_used: int = 0
    sources: list[ChatSourceItem] = Field(default_factory=list)
    disclaimer: str
    remaining_quota: int | None = Field(
        default=None,
        description="Remaining guest quota. Null for authenticated/premium users.",
    )


class ChatHistoryItem(BaseModel):
    """Single persisted chat history item."""

    id: str
    document_id: str
    question: str
    answer: str
    sources: list[ChatSourceItem] = Field(default_factory=list)
    created_at: str


class ChatHistoryResponse(BaseModel):
    """Response payload for chat history endpoint."""

    document_id: str
    items: list[ChatHistoryItem] = Field(default_factory=list)
