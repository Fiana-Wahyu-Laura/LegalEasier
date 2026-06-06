"""
Pydantic schemas for Document API requests/responses.
"""

import os
import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, computed_field


class DocumentListItem(BaseModel):
    """Lightweight response schema for document lists.

    Excludes heavy fields (storage_path, extracted_text, file_content)
    to keep list responses fast and payload-efficient.
    """

    id: uuid.UUID
    filename: str
    status: str
    summary: Optional[str] = None
    risk_score: Optional[int] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

    @computed_field
    @property
    def has_analysis(self) -> bool:
        """True when the document has been fully processed."""
        return self.status == "done"

    @computed_field
    @property
    def file_type(self) -> Optional[str]:
        """File extension derived from filename (e.g. 'pdf', 'png')."""
        _, ext = os.path.splitext(self.filename)
        return ext.lstrip(".").lower() if ext else None

    @computed_field
    @property
    def risk_level(self) -> Optional[str]:
        """Human-readable risk level derived from risk_score."""
        if self.risk_score is None:
            return None
        if self.risk_score <= 20:
            return "Aman"
        if self.risk_score <= 40:
            return "Rendah"
        if self.risk_score <= 70:
            return "Sedang"
        return "Tinggi"


class DocumentResponse(BaseModel):
    """Full response schema for single document detail."""

    id: uuid.UUID
    filename: str
    status: str
    extracted_text: Optional[str] = None
    summary: Optional[str] = None
    risk_score: Optional[int] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DocumentStatusResponse(BaseModel):
    """Response schema for document status."""

    id: uuid.UUID
    status: str


class DocumentTextResponse(BaseModel):
    """Response schema for extracted text."""

    id: uuid.UUID
    extracted_text: str
    status: str

class RiskClauseResponse(BaseModel):
    clause_text: str
    plain_language: str
    risk_level: str  # "Tinggi", "Sedang", "Rendah", "Aman"
    confidence: float

class DocumentAnalysisResponse(BaseModel):
    document_id: uuid.UUID
    summary: Optional[str] = None
    risk_score: Optional[int] = None
    risk_clauses: list[RiskClauseResponse] = []
    disclaimer: str = "Hasil ini bersifat informatif dan bukan pengganti konsultasi hukum profesional."