import json
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status, Header
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.models.document import Document
from app.schemas.auth import AuthUser
from app.schemas.common import StandardResponse
from app.schemas.document import DocumentAnalysisResponse, RiskClauseResponse

router = APIRouter(prefix="/documents", tags=["analysis"])


@router.get("/{document_id}/analysis", response_model=StandardResponse)
async def get_document_analysis(
    document_id: uuid.UUID,
    current_user: AuthUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> StandardResponse:
    """Get analysis result for a document. Only owner can access (CLAUDE.md §8)."""
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

    # Parse risk_clauses dari JSON string
    risk_clauses: list[RiskClauseResponse] = []
    if document.risk_clauses_json:
        try:
            raw = json.loads(document.risk_clauses_json)
            risk_clauses = [RiskClauseResponse(**item) for item in raw]
        except (json.JSONDecodeError, TypeError):
            risk_clauses = []

    analysis = DocumentAnalysisResponse(
        document_id=document.id,
        summary=document.summary,
        risk_score=document.risk_score,
        risk_clauses=risk_clauses,
    )
    return StandardResponse(
        success=True,
        data=analysis.model_dump(mode="json"),
        message="Analysis result retrieved.",
    )