import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, ForeignKey, Index, Integer, LargeBinary, String, Text
from sqlalchemy.dialects.postgresql import UUID

from app.models.base import Base


class Document(Base):
    __tablename__ = "documents"

    id: uuid.UUID = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    owner_id: uuid.UUID | None = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    filename: str = Column(String(1024), nullable=False)
    storage_path: str = Column(String(2048), nullable=False)
    file_content: bytes | None = Column(LargeBinary(), nullable=True)
    status: str = Column(String(32), nullable=False, default="pending")
    extracted_text: str | None = Column(Text, nullable=True)
    summary: str | None = Column(Text, nullable=True)
    risk_score: int | None = Column(Integer, nullable=True)
    risk_clauses_json: str | None = Column(Text, nullable=True)
    created_at: datetime = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at: datetime = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    __table_args__ = (
        Index("ix_documents_owner_id", "owner_id"),
        Index("ix_documents_status", "status"),
    )
