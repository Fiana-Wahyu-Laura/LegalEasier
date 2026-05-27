"""
Schemas for the backend ↔ NLP service contract.
"""

from __future__ import annotations

from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


FileType = Literal["pdf", "jpg", "png", "tiff"]
RiskLevel = Literal["Tinggi", "Sedang", "Rendah", "Aman"]


class NLPProcessRequest(BaseModel):
    """Metadata fields sent alongside the multipart file upload."""

    document_id: UUID
    file_type: FileType


class NLPRiskClause(BaseModel):
    clause_text: str
    plain_language: str
    risk_level: RiskLevel
    confidence: float = Field(ge=0.0, le=1.0)


class NLPProcessResponse(BaseModel):
    document_id: UUID
    ocr_used: bool
    full_text: str
    summary: str
    risk_score: int = Field(ge=0, le=100)
    risk_clauses: list[NLPRiskClause]
    disclaimer: str

    model_config = ConfigDict(extra="ignore")


class NLPChatHistoryItem(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1)


class NLPChatRequest(BaseModel):
    document_id: str
    query: str = Field(min_length=1)
    history: list[NLPChatHistoryItem] = Field(default_factory=list, max_length=20)
    top_k: int = Field(default=5, ge=1, le=10)


class NLPChatResponse(BaseModel):
    document_id: str
    query: str
    answer: str
    context_chunks_used: int = 0
    context_chunks: list[str] = Field(default_factory=list)
    suggestions: list[str] = Field(default_factory=list)
    disclaimer: str

    model_config = ConfigDict(extra="ignore")
