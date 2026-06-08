"""
Guest AI quota helpers.

Guest users get a limited number of AI analysis attempts. The backend owns this
limit because frontend-only SharedPreferences can be reset by the client.
"""

import uuid
from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.guest_quota import GuestQuota

DEFAULT_GUEST_FREE_ANALYSES = 5
GUEST_QUOTA_EXHAUSTED_DETAIL = (
    "Kuota gratis tamu sudah habis. Silakan daftar untuk melanjutkan analisis tanpa batas."
)


async def get_or_create_guest_quota(
    db: AsyncSession,
    user_id: uuid.UUID,
    *,
    for_update: bool = False,
) -> GuestQuota:
    """Return a guest quota row, creating it with the default allowance if missing."""
    stmt = select(GuestQuota).where(GuestQuota.user_id == user_id)
    if for_update:
        stmt = stmt.with_for_update()

    result = await db.execute(stmt)
    quota = result.scalar_one_or_none()
    if quota is not None:
        return quota

    quota = GuestQuota(user_id=user_id, remaining_quota=DEFAULT_GUEST_FREE_ANALYSES)
    db.add(quota)
    await db.flush()
    return quota


async def ensure_guest_quota_available(db: AsyncSession, user_id: uuid.UUID) -> int:
    """Return remaining guest quota or raise 429 if no AI attempts remain."""
    quota = await get_or_create_guest_quota(db, user_id)
    if quota.remaining_quota <= 0:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=GUEST_QUOTA_EXHAUSTED_DETAIL,
        )
    return quota.remaining_quota


async def consume_guest_quota(db: AsyncSession, user_id: uuid.UUID) -> int:
    """Consume one guest AI attempt and return the remaining quota."""
    quota = await get_or_create_guest_quota(db, user_id, for_update=True)
    if quota.remaining_quota <= 0:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=GUEST_QUOTA_EXHAUSTED_DETAIL,
        )

    quota.remaining_quota -= 1
    quota.last_reset = datetime.now(timezone.utc)
    await db.flush()
    return quota.remaining_quota
