"""
Guest quota API routes.

Provides server-authoritative guest quota information so the frontend
can stay in sync (single source of truth principle).

Per CLAUDE.md §8: All endpoints except /auth/* require Bearer JWT token.
"""

import logging

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.schemas.auth import AuthUser
from app.schemas.common import StandardResponse
from app.services.guest_quota import (
    DEFAULT_GUEST_FREE_ANALYSES,
    get_or_create_guest_quota,
    consume_guest_quota,
    ensure_guest_quota_available,
    refund_guest_quota,
)

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
