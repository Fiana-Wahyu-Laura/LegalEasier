import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, ForeignKey, Integer
from sqlalchemy.dialects.postgresql import UUID

from app.models.base import Base


class GuestQuota(Base):
    __tablename__ = "guest_quotas"

    user_id: uuid.UUID = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
        nullable=False,
    )
    remaining_quota: int = Column(Integer, nullable=False, default=5)
    last_reset: datetime = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
